import fs from 'node:fs/promises'
import path from 'node:path'

const ROOT_DIR = path.resolve(
    import.meta.dirname,
    '../..',
)

const API_BASE =
    'https://api.checklistbank.org/dataset/3LXR'

const CHILD_LIMIT = 100_000

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
}

type COLTreeResponse = {
    offset?: number
    limit?: number
    total?: number
    empty?: boolean
    last?: boolean
    result?: COLTreeNode[]
}

type ProcessedTaxon = {
    id: string
    parentId: string | null
    name: string
    rank: string | null
    status: string | null
    childCount: number
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


// 

async function askLLM(
    prompt: string,
): Promise<string> {
    const response = await fetch(
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
            `LLM request failed: ${response.status} ${response.statusText}`,
        )
    }

    const data = await response.json() as {
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

//
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
            `COL request failed: ${response.status} ${response.statusText} \n${url} `,
        )
    }

    return response.json() as Promise<T>
}

/*
 * ============================================================
 * COL tree requests
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
                !isExcludedIdentifier(node),
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
     * A taxon with childCount=0 is known to be a leaf.
     * Do not make an API request.
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
     * COL omits result[] when the taxon has no children.
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
}

/*
 * ============================================================
 * Normalization
 * ============================================================
 */

function toProcessedTaxon(
    node: COLTreeNode,
): ProcessedTaxon | null {
    const id =
        node.id?.trim()

    const name =
        node.name?.trim()

    if (!id || !name) {
        return null
    }

    return {
        id,

        parentId:
            node.parentId?.trim() ??
            null,

        name,

        rank:
            node.rank?.trim() ??
            null,

        status:
            node.status?.trim() ??
            null,

        childCount:
            node.childCount ?? 0,
    }
}

/*
 * ============================================================
 * Main traversal
 * ============================================================
 */

async function processCOL(): Promise<void> {
    console.log(
        'Starting Catalogue of Life traversal...',
    )

    const outputDir =
        path.join(
            ROOT_DIR,
            'data',
            'processed',
        )

    await fs.mkdir(
        outputDir,
        {
            recursive: true,
        },
    )

    const root =
        await fetchRoot()

    console.log(
        `Root taxa: ${root.length}`,
    )

    const taxon = root[0]

    if (!taxon) {
        throw new Error(
            'No root taxon returned.',
        )
    }

    const taxonName =
        taxon.name ?? 'unknown'

    const prompt =
        `What is ${taxonName}?`

    console.log(
        `Asking LLM: ${prompt}`,
    )

    const llmResponse =
        await askLLM(prompt)

    console.log()
    console.log('LLM response:')
    console.log(llmResponse)

    return

    ////////////
    /*
     * Explicit stack = depth-first traversal.
     */
    // const stack =
    //     [...root]

    // const visited =
    //     new Set<string>()

    // const processed:
    //     ProcessedTaxon[] = []

    // let processedCount = 0
    // let skippedCount = 0
    // let failedCount = 0

    // while (
    //     stack.length > 0
    // ) {
    //     const taxon =
    //         stack.pop()

    //     if (!taxon) {
    //         continue
    //     }

    //     const id =
    //         taxon.id?.trim()

    //     if (!id) {
    //         skippedCount++
    //         continue
    //     }

    //     if (
    //         visited.has(id)
    //     ) {
    //         continue
    //     }

    //     visited.add(id)

    //     /*
    //      * Skip BOLD / SH identifier nodes entirely.
    //      */
    //     if (
    //         isExcludedIdentifier(
    //             taxon,
    //         )
    //     ) {
    //         skippedCount++
    //         continue
    //     }

    //     /*
    //      * Store the taxon itself.
    //      */
    //     const processedTaxon =
    //         toProcessedTaxon(
    //             taxon,
    //         )

    //     if (
    //         processedTaxon
    //     ) {
    //         processed.push(
    //             processedTaxon,
    //         )
    //     } else {
    //         skippedCount++
    //         continue
    //     }

    //     processedCount++

    //     /*
    //      * Leaves require no request.
    //      */
    //     if (
    //         taxon.childCount === 0
    //     ) {
    //         continue
    //     }

    //     /*
    //      * Fetch this taxon's complete direct children.
    //      *
    //      * If the request fails, simply skip this branch for now.
    //      */
    //     let children:
    //         COLTreeNode[]

    //     try {
    //         children =
    //             await fetchChildren(
    //                 taxon,
    //             )
    //     } catch (error) {
    //         failedCount++

    //         console.error(
    //             `Skipping failed taxon: ${id} (${taxon.name ?? 'unnamed'})`,
    //         )

    //         console.error(
    //             error,
    //         )

    //         continue
    //     }

    // /*
    //  * Add valid children to the traversal stack.
    //  */
    // for (
    //     const child of children
    // ) {
    //     const childId =
    //         child.id?.trim()

    //     if (!childId) {
    //         skippedCount++
    //         continue
    //     }

    //     if (
    //         visited.has(
    //             childId,
    //         )
    //     ) {
    //         continue
    //     }

    //     if (
    //         isExcludedIdentifier(
    //             child,
    //         )
    //     ) {
    //         skippedCount++
    //         continue
    //     }

    //     stack.push(child)
    // }

    // /*
    //  * Progress reporting.
    //  */
    // if (
    //     processedCount % 1_000 === 0
    // ) {
    //     console.log(
    //         `Processed: ${processedCount.toLocaleString()} | ` +
    //         `Queued: ${stack.length.toLocaleString()} | ` +
    //         `Skipped: ${skippedCount.toLocaleString()} | ` +
    //         `Failed: ${failedCount.toLocaleString()}`,
    //     )
    // }
    // }

    // /*
    //  * ============================================================
    //  * Output
    //  * ============================================================
    //  */

    // const outputPath =
    //     path.join(
    //         outputDir,
    //         'col-taxa.json',
    //     )

    // await fs.writeFile(
    //     outputPath,
    //     JSON.stringify(
    //         processed,
    //         null,
    //         2,
    //     ),
    //     'utf8',
    // )

    // console.log()
    // console.log(
    //     'Catalogue of Life traversal complete.',
    // )
    // console.log(
    //     `Processed: ${processedCount.toLocaleString()}`,
    // )
    // console.log(
    //     `Stored: ${processed.length.toLocaleString()}`,
    // )
    // console.log(
    //     `Skipped: ${skippedCount.toLocaleString()}`,
    // )
    // console.log(
    //     `Failed: ${failedCount.toLocaleString()}`,
    // )
    // console.log(
    //     `Output: ${outputPath}`,
    // )
}

processCOL().catch(
    (error: unknown) => {
        console.error()
        console.error(
            'Catalogue of Life processing failed.',
        )
        console.error(error)

        process.exitCode = 1
    },
)