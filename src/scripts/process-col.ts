import fs from 'node:fs/promises'
import path from 'node:path'

const ROOT_DIR = path.resolve(
    import.meta.dirname,
    '../..',
)

const API_BASE =
    'https://api.checklistbank.org/dataset/3LXR'

const CHILD_LIMIT = 1_000_000

const SYSTEM_PROMPT_PATH =
    path.join(
        import.meta.dirname,
        'system_prompt.txt',
    )

type COLTreeNode = {
    id?: string
    parentId?: string
    rank?: string
    status?: string
    count?: number
    childCount?: number
    name?: string
    labelHtml?: string
    type?: string
    authorship?: string
}

type COLTreeResponse = {
    offset?: number
    limit?: number
    total?: number
    empty?: boolean
    last?: boolean
    result?: COLTreeNode[]
}

type COLTaxonInfo = {
    id?: string
    datasetKey?: number
    name?: {
        scientificName?: string
        authorship?: string
        rank?: string
        uninomial?: string
        origin?: string
        type?: string
    }
    status?: string
    origin?: string
    label?: string
    labelHtml?: string
}

type COLVernacular = {
    name?: string
    language?: string
    languageCode?: string
    country?: string
}

type TraversalItem = {
    taxon: COLTreeNode
    path: COLTreeNode[]
}

/*
 * ============================================================
 * Identifier filtering
 * ============================================================
 *
 * Exclude:
 *
 *   BOLD:...
 *
 * and UNITE SH identifiers such as:
 *
 *   SH1414389.10FU
 *   SH1158201.09FU
 */

function isExcludedIdentifier(
    node: COLTreeNode,
): boolean {
    const id =
        node.id?.trim() ?? ''

    const name =
        node.name?.trim() ?? ''

    return (
        /^BOLD:/i.test(id) ||
        /^BOLD:/i.test(name) ||
        /^SH\d+\.\d{1,2}FU$/i.test(id) ||
        /^SH\d+\.\d{1,2}FU$/i.test(name)
    )
}

/*
 * ============================================================
 * LLM
 * ============================================================
 */

async function loadSystemPrompt(): Promise<string> {
    return fs.readFile(
        SYSTEM_PROMPT_PATH,
        'utf8',
    )
}

async function askLLM(
    prompt: string,
): Promise<string> {
    const response =
        await fetch(
            'http://127.0.0.1:8765/chat',
            {
                method: 'POST',
                headers: {
                    'Content-Type':
                        'application/json',
                },
                body: JSON.stringify({
                    prompt,
                }),
            },
        )

    if (!response.ok) {
        throw new Error(
            `LLM request failed: ${response.status} ${response.statusText} `,
        )
    }

    const data =
        await response.json() as {
            ok: boolean
            response?: string
        }

    if (!data.ok) {
        throw new Error(
            'LLM returned ok=false',
        )
    }

    if (!data.response) {
        throw new Error(
            'LLM response was empty.',
        )
    }

    return data.response
}

function hasSQLReady(
    response: string,
): boolean {
    const tag =
        '[SQL_READY]'

    const first =
        response.indexOf(tag)

    if (first === -1) {
        return false
    }

    const second =
        response.indexOf(
            tag,
            first + tag.length,
        )

    return second !== -1
}

function extractSQLReadyPayload(
    response: string,
): string {
    const tag =
        '[SQL_READY]'

    const start =
        response.indexOf(tag)

    const end =
        response.indexOf(
            tag,
            start + tag.length,
        )

    if (
        start === -1 ||
        end === -1
    ) {
        throw new Error(
            'SQL_READY response does not contain two SQL_READY tags.',
        )
    }

    return response
        .slice(
            start + tag.length,
            end,
        )
        .trim()
}

/*
 * ============================================================
 * HTTP
 * ============================================================
 */

async function fetchJSON<T>(
    url: string,
): Promise<T> {
    const response =
        await fetch(url)

    if (!response.ok) {
        throw new Error(
            `Request failed: ${response.status} ${response.statusText} \n${url} `,
        )
    }

    return response.json() as Promise<T>
}

/*
 * ============================================================
 * COL tree
 * ============================================================
 */

async function fetchRoot(): Promise<
    COLTreeNode[]
> {
    const data =
        await fetchJSON<COLTreeResponse>(
            `${API_BASE}/tree?limit=${CHILD_LIMIT}`,
        )

    return (data.result ?? [])
        .filter(
            (node) =>
                !isExcludedIdentifier(
                    node,
                ),
        )
}

async function fetchChildren(
    taxon: COLTreeNode,
): Promise<COLTreeNode[]> {
    const taxonId =
        taxon.id?.trim()

    if (!taxonId) {
        throw new Error(
            'Taxon has no ID.',
        )
    }

    /*
     * COL already tells us whether this taxon has children.
     * Avoid an API request for known leaves.
     */
    if (
        taxon.childCount === 0
    ) {
        return []
    }

    const url =
        `${API_BASE}/tree/${encodeURIComponent(
            taxonId,
        )}/children?limit=${CHILD_LIMIT}`

    const data =
        await fetchJSON<COLTreeResponse>(
            url,
        )

    /*
     * COL omits result[] for empty child responses.
     */
    if (
        data.empty === true ||
        data.total === 0
    ) {
        return []
    }

    if (
        !Array.isArray(data.result)
    ) {
        throw new Error(
            `Unexpected COL response for ${taxonId}\n` +
            `${url}\n` +
            JSON.stringify(
                data,
                null,
                2,
            ),
        )
    }

    return data.result
        .filter(
            (node) =>
                !isExcludedIdentifier(
                    node,
                ),
        )
}

/*
 * ============================================================
 * COL taxon metadata
 * ============================================================
 */

async function fetchTaxonInfo(
    taxonId: string,
): Promise<COLTaxonInfo> {
    return fetchJSON<COLTaxonInfo>(
        `${API_BASE}/taxon/${encodeURIComponent(
            taxonId,
        )}`,
    )
}

async function fetchVernacular(
    taxonId: string,
): Promise<COLVernacular[]> {
    const data =
        await fetchJSON<
            COLVernacular[] |
            {
                result?: COLVernacular[]
            }
        >(
            `${API_BASE}/taxon/${encodeURIComponent(
                taxonId,
            )}/vernacular`,
        )

    if (Array.isArray(data)) {
        return data
    }

    return data.result ?? []
}

/*
 * ============================================================
 * Prompt preparation
 * ============================================================
 */

function formatCommonNames(
    names: COLVernacular[],
): string {
    const uniqueNames =
        [
            ...new Set(
                names
                    .map(
                        (item) =>
                            item.name?.trim(),
                    )
                    .filter(
                        (
                            name,
                        ): name is string =>
                            Boolean(name),
                    ),
            ),
        ]

    if (
        uniqueNames.length === 0
    ) {
        return 'None provided by Catalogue of Life.'
    }

    return uniqueNames
        .map(
            (name) =>
                `- ${name}`,
        )
        .join('\n')
}

function formatTaxonPath(
    path: COLTreeNode[],
): string {
    return path
        .map(
            (node) =>
                node.name?.trim() ??
                'Unknown',
        )
        .join(' → ')
}

function createInitialPrompt(
    systemPrompt: string,
    taxon: COLTreeNode,
    taxonInfo: COLTaxonInfo,
    vernacular: COLVernacular[],
    taxonPath: COLTreeNode[],
): string {
    const scientificName =
        taxonInfo.name
            ?.scientificName ??
        taxon.name ??
        'Unknown'

    const authorship =
        taxonInfo.name
            ?.authorship ??
        taxon.authorship ??
        'Not provided by Catalogue of Life.'

    const rank =
        taxonInfo.name
            ?.rank ??
        taxon.rank ??
        'Not provided by Catalogue of Life.'

    return `${systemPrompt}

---

CATALOGUE OF LIFE INFORMATION

Scientific name:
${scientificName}

Authorship:
${authorship}

Taxonomic rank:
${rank}

Taxonomic path:
${formatTaxonPath(taxonPath)}

Catalogue of Life common names:
${formatCommonNames(vernacular)}

Use the Catalogue of Life information above as authoritative
starting context.

Preserve useful Catalogue of Life common names in the final
profile and add additional well-supported common names when
they exist.

Do not invent common names.

Begin your research and enrichment process.

What is ${scientificName}?
`
}

/*
 * ============================================================
 * LLM enrichment
 * ============================================================
 */

async function enrichTaxon(
    systemPrompt: string,
    taxon: COLTreeNode,
    taxonInfo: COLTaxonInfo,
    vernacular: COLVernacular[],
    taxonPath: COLTreeNode[],
): Promise<string> {
    const scientificName =
        taxonInfo.name
            ?.scientificName ??
        taxon.name ??
        'Unknown'

    const authorship =
        taxonInfo.name
            ?.authorship ??
        taxon.authorship ??
        'Not provided by Catalogue of Life.'

    const rank =
        taxonInfo.name
            ?.rank ??
        taxon.rank ??
        'Not provided by Catalogue of Life.'

    const formattedPath =
        formatTaxonPath(
            taxonPath,
        )

    let prompt =
        createInitialPrompt(
            systemPrompt,
            taxon,
            taxonInfo,
            vernacular,
            taxonPath,
        )

    let pass = 0

    while (true) {
        pass++

        console.log()
        console.log(
            `========== ${scientificName} — LLM PASS ${pass} ==========`,
        )

        const response =
            await askLLM(
                prompt,
            )

        console.log()
        console.log(
            response,
        )

        if (
            hasSQLReady(
                response,
            )
        ) {
            return extractSQLReadyPayload(
                response,
            )
        }

        prompt =
            `${systemPrompt}

---

CATALOGUE OF LIFE INFORMATION

Scientific name:
${scientificName}

Authorship:
${authorship}

Taxonomic rank:
${rank}

Taxonomic path:
${formattedPath}

Catalogue of Life common names:
${formatCommonNames(vernacular)}

---

PREVIOUS PASS

${response}

---

The previous pass was not finalized.

Continue researching, reasoning, checking for missing or
uncertain information, and improving the profile.

Do not finalize until you are genuinely ready.

When ready, the complete final payload MUST appear between
two [SQL_READY] tags.

For now:

[CONTINUE]
`
    }
}

/*
 * ============================================================
 * Main traversal
 * ============================================================
 */

async function processCOL(): Promise<void> {
    console.log(
        'Starting Catalogue of Life processing...',
    )

    const systemPrompt =
        await loadSystemPrompt()

    const root =
        await fetchRoot()

    console.log(
        `Root taxa: ${root.length}`,
    )

    /*
     * Each stack entry carries the complete ancestry needed
     * to build the taxonomic path for the LLM.
     *
     * Life itself is represented as the first path node.
     */
    const lifeNode: COLTreeNode = {
        id: 'life',
        name: 'Life',
        rank: 'root',
    }

    /*
     * Push roots in reverse order so the first root returned
     * by COL is processed first by the depth-first stack.
     */
    const stack:
        TraversalItem[] = root
            .slice()
            .reverse()
            .map(
                (taxon) => ({
                    taxon,
                    path: [
                        lifeNode,
                        taxon,
                    ],
                }),
            )

    /*
     * Prevent duplicate traversal of the same COL taxon.
     */
    const visited =
        new Set<string>()

    let processedCount = 0
    let skippedCount = 0
    let failedCount = 0

    while (
        stack.length > 0
    ) {
        const item =
            stack.pop()

        if (!item) {
            continue
        }

        const {
            taxon,
            path: taxonPath,
        } = item

        const taxonId =
            taxon.id?.trim()

        if (!taxonId) {
            skippedCount++

            console.log(
                'Skipping taxon without an ID.',
            )

            continue
        }

        if (
            visited.has(
                taxonId,
            )
        ) {
            continue
        }

        visited.add(
            taxonId,
        )

        /*
         * Identifier records should never enter the
         * enrichment pipeline.
         */
        if (
            isExcludedIdentifier(
                taxon,
            )
        ) {
            skippedCount++
            continue
        }

        const scientificName =
            taxon.name ??
            taxonId

        console.log()
        console.log(
            '============================================================',
        )
        console.log(
            `PROCESSING TAXON ${processedCount + 1}`,
        )
        console.log(
            `Name: ${scientificName}`,
        )
        console.log(
            `ID: ${taxonId}`,
        )
        console.log(
            `Rank: ${taxon.rank ?? 'unknown'}`,
        )
        console.log(
            `Children: ${(taxon.childCount ?? 0).toLocaleString()}`,
        )
        console.log(
            `Path: ${formatTaxonPath(taxonPath)}`,
        )
        console.log(
            '============================================================',
        )

        /*
         * ========================================================
         * Fetch detailed COL metadata
         * ========================================================
         */

        let taxonInfo:
            COLTaxonInfo

        let vernacular:
            COLVernacular[]

        try {
            taxonInfo =
                await fetchTaxonInfo(
                    taxonId,
                )

            vernacular =
                await fetchVernacular(
                    taxonId,
                )
        } catch (error) {
            failedCount++

            console.error(
                `Skipping failed metadata request: ${taxonId} (${scientificName})`,
            )

            console.error(
                error,
            )

            continue
        }

        /*
         * ========================================================
         * Enrich with LLM
         * ========================================================
         */

        let finalPayload:
            string

        try {
            finalPayload =
                await enrichTaxon(
                    systemPrompt,
                    taxon,
                    taxonInfo,
                    vernacular,
                    taxonPath,
                )
        } catch (error) {
            failedCount++

            console.error(
                `Skipping failed LLM processing: ${taxonId} (${scientificName})`,
            )

            console.error(
                error,
            )

            continue
        }

        processedCount++

        console.log()
        console.log(
            '========== SQL_READY PAYLOAD ==========',
        )
        console.log(
            finalPayload,
        )

        /*
         * ========================================================
         * Leaves need no children request.
         * ========================================================
         */

        if (
            taxon.childCount === 0
        ) {
            continue
        }

        /*
         * ========================================================
         * Fetch direct children
         * ========================================================
         */

        let children:
            COLTreeNode[]

        try {
            children =
                await fetchChildren(
                    taxon,
                )
        } catch (error) {
            failedCount++

            console.error(
                `Skipping failed child traversal: ${taxonId} (${scientificName})`,
            )

            console.error(
                error,
            )

            continue
        }

        /*
         * Reverse before pushing so the alphabetically/API
         * ordered first child is processed first.
         */
        for (
            let index =
                children.length - 1;
            index >= 0;
            index--
        ) {
            const child =
                children[index]

            if (!child) {
                continue
            }

            const childId =
                child.id?.trim()

            if (!childId) {
                skippedCount++
                continue
            }

            if (
                visited.has(
                    childId,
                )
            ) {
                continue
            }

            if (
                isExcludedIdentifier(
                    child,
                )
            ) {
                skippedCount++
                continue
            }

            stack.push({
                taxon: child,
                path: [
                    ...taxonPath,
                    child,
                ],
            })
        }

        /*
         * Progress reporting.
         */
        console.log()
        console.log(
            `Processed: ${processedCount.toLocaleString()} | ` +
            `Queued: ${stack.length.toLocaleString()} | ` +
            `Skipped: ${skippedCount.toLocaleString()} | ` +
            `Failed: ${failedCount.toLocaleString()}`,
        )
    }

    console.log()
    console.log(
        '============================================================',
    )
    console.log(
        'Catalogue of Life traversal complete.',
    )
    console.log(
        `Processed: ${processedCount.toLocaleString()}`,
    )
    console.log(
        `Skipped: ${skippedCount.toLocaleString()}`,
    )
    console.log(
        `Failed: ${failedCount.toLocaleString()}`,
    )
    console.log(
        '============================================================',
    )

    /*
     * ============================================================
     * FUTURE — SQLITE OUTPUT
     * ============================================================
     *
     * The final SQL_READY payload will eventually be parsed and
     * inserted into:
     *
     *   data/lifesql-local-staging.sqlite
     *
     * using the LifeSQL staging schema.
     *
     * We intentionally keep database writes disabled while the
     * enrichment workflow is still being validated.
     */
}

processCOL().catch(
    (error: unknown) => {
        console.error()
        console.error(
            'Catalogue of Life processing failed.',
        )
        console.error(
            error,
        )

        process.exitCode = 1
    },
)