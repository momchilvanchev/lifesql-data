import readline from 'node:readline/promises'
import {
    stdin as input,
    stdout as output,
} from 'node:process'

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

function compareNames(
    a: COLTreeNode,
    b: COLTreeNode,
): number {
    return (
        (a.name ?? '').localeCompare(
            b.name ?? '',
            undefined,
            {
                sensitivity: 'base',
            },
        )
    )
}

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
        .sort(compareNames)
}

async function fetchChildren(
    taxon: COLTreeNode,
): Promise<COLTreeNode[]> {
    const taxonId =
        taxon.id?.trim()

    if (!taxonId) {
        throw new Error(
            'Cannot fetch children: taxon has no ID.',
        )
    }

    /*
     * Important optimization:
     *
     * COL already tells us whether this taxon has children.
     * Do not make an API request for a known leaf.
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
     * COL represents an empty child list by omitting `result`
     * and returning total=0 / empty=true.
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
            `Unexpected COL response for ${taxonId}\n${url}\n` +
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
        .sort(compareNames)
}

function formatTaxon(
    node: COLTreeNode,
): string {
    const name =
        node.name ??
        '(unnamed)'

    const rank =
        node.rank ??
        'unknown rank'

    const id =
        node.id ??
        '?'

    const childCount =
        node.childCount ??
        0

    return (
        `${name} ` +
        `(${rank}, ` +
        `${childCount.toLocaleString()} children, ` +
        `ID: ${id})`
    )
}

async function chooseChild(
    rl: readline.Interface,
    children: COLTreeNode[],
): Promise<
    number | 'back' | 'quit'
> {
    console.log()

    for (
        let index = 0;
        index < children.length;
        index++
    ) {
        const child =
            children[index]

        if (!child) {
            continue
        }

        console.log(
            `  ${index + 1}. ${formatTaxon(child)}`,
        )
    }

    console.log()
    console.log(
        'Enter a number, "b" to go back, or "q" to quit.',
    )

    while (true) {
        const answer =
            (
                await rl.question(
                    '> ',
                )
            )
                .trim()
                .toLowerCase()

        if (
            answer === 'q'
        ) {
            return 'quit'
        }

        if (
            answer === 'b'
        ) {
            return 'back'
        }

        const number =
            Number(answer)

        if (
            Number.isInteger(
                number,
            ) &&
            number >= 1 &&
            number <=
            children.length
        ) {
            return number - 1
        }

        console.log(
            `Choose a number from 1-${children.length}, "b", or "q".`,
        )
    }
}

async function main(): Promise<void> {
    const rl =
        readline.createInterface({
            input,
            output,
        })

    /*
     * Stack of previously visited taxa.
     *
     * This gives us manual back navigation without making
     * any assumptions about the eventual data pipeline.
     */
    const history:
        COLTreeNode[] = []

    try {
        console.log()
        console.log(
            'LifeSQL — Catalogue of Life manual traversal',
        )
        console.log()
        console.log(
            `Child request limit: ${CHILD_LIMIT.toLocaleString()}`,
        )
        console.log(
            'Children are sorted alphabetically.',
        )
        console.log(
            'BOLD and SH identifiers are filtered.',
        )
        console.log()

        let children =
            await fetchRoot()

        /*
         * The five COL root nodes are presented as the first
         * selectable level.
         */
        let current:
            COLTreeNode | null = null

        while (true) {
            /*
             * Display the current taxon before showing its children.
             */
            if (current) {
                console.log()
                console.log(
                    '--------------------------------------------------',
                )
                console.log(
                    formatTaxon(current),
                )
                console.log(
                    '--------------------------------------------------',
                )

                /*
                 * Known leaf: do not make an API request.
                 */
                if (
                    current.childCount === 0
                ) {
                    console.log(
                        'Leaf taxon — no children to traverse.',
                    )

                    const answer =
                        (
                            await rl.question(
                                '\nPress "b" to go back or "q" to quit: ',
                            )
                        )
                            .trim()
                            .toLowerCase()

                    if (
                        answer === 'q'
                    ) {
                        break
                    }

                    if (
                        answer === 'b'
                    ) {
                        current =
                            history.pop() ??
                            null

                        if (
                            current
                        ) {
                            children =
                                await fetchChildren(
                                    current,
                                )
                        } else {
                            children =
                                await fetchRoot()
                        }

                        continue
                    }

                    console.log(
                        'Please enter "b" or "q".',
                    )

                    continue
                }

                /*
                 * Fetch only when we actually arrive at this taxon.
                 */
                children =
                    await fetchChildren(
                        current,
                    )

                if (
                    children.length === 0
                ) {
                    console.log(
                        'COL returned no children.',
                    )

                    const answer =
                        (
                            await rl.question(
                                '\nPress "b" to go back or "q" to quit: ',
                            )
                        )
                            .trim()
                            .toLowerCase()

                    if (
                        answer === 'q'
                    ) {
                        break
                    }

                    if (
                        answer === 'b'
                    ) {
                        current =
                            history.pop() ??
                            null

                        if (
                            current
                        ) {
                            children =
                                await fetchChildren(
                                    current,
                                )
                        } else {
                            children =
                                await fetchRoot()
                        }

                        continue
                    }

                    continue
                }
            }

            /*
             * Show the current level and let the user choose
             * which branch to explore next.
             */
            const choice =
                await chooseChild(
                    rl,
                    children,
                )

            if (
                choice === 'quit'
            ) {
                break
            }

            if (
                choice === 'back'
            ) {
                if (
                    history.length === 0
                ) {
                    console.log(
                        'Already at the root.',
                    )
                    continue
                }

                current =
                    history.pop() ??
                    null

                if (
                    current
                ) {
                    children =
                        await fetchChildren(
                            current,
                        )
                } else {
                    children =
                        await fetchRoot()
                }

                continue
            }

            const selected =
                children[choice]

            if (
                !selected
            ) {
                continue
            }

            /*
             * Save the current node before moving deeper.
             *
             * At the root there is no current taxon, so only
             * actual taxa are added to history.
             */
            if (
                current
            ) {
                history.push(
                    current,
                )
            }

            current =
                selected

            /*
             * The loop now stops on this taxon and requires
             * another explicit choice before going deeper.
             */
        }
    } finally {
        rl.close()
    }
}

main().catch(
    (error: unknown) => {
        console.error()
        console.error(
            'Catalogue of Life traversal failed.',
        )
        console.error(error)
        process.exitCode = 1
    },
)