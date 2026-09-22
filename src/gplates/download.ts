import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

import { MAP_SNAPSHOTS } from './snapshots.ts'

const BASE_URL =
    'https://gws.gplates.org/reconstruct/coastlines/'

const MODEL =
    'MULLER2022'

const OUTPUT_DIRECTORY =
    'data/raw/gplates/muller2022/coastlines'

function getSnapshotFilename(
    index: number,
    snapshot: typeof MAP_SNAPSHOTS[number],
) {
    const order =
        String(index + 1).padStart(2, '0')

    const age =
        snapshot.timeMa === 0
            ? '0Ma'
            : `${snapshot.timeMa}Ma`

    return `${order}-${snapshot.id}-${age}.geojson`
}

async function downloadSnapshot(
    index: number,
    snapshot: typeof MAP_SNAPSHOTS[number],
) {
    const url =
        new URL(BASE_URL)

    url.searchParams.set(
        'time',
        String(snapshot.timeMa),
    )

    url.searchParams.set(
        'model',
        MODEL,
    )

    const filename =
        getSnapshotFilename(
            index,
            snapshot,
        )

    const outputPath =
        join(
            OUTPUT_DIRECTORY,
            filename,
        )

    console.log(
        `[download] ${snapshot.id} (${snapshot.timeMa} Ma)`,
    )

    const response =
        await fetch(url)

    if (!response.ok) {
        throw new Error(
            `${snapshot.id}: HTTP ${response.status} ${response.statusText}`,
        )
    }

    const text =
        await response.text()

    await writeFile(
        outputPath,
        text,
        'utf8',
    )

    console.log(
        `[saved] ${outputPath} (${text.length.toLocaleString()} bytes)`,
    )
}

async function main() {
    await mkdir(
        OUTPUT_DIRECTORY,
        { recursive: true },
    )

    for (
        let index = 0;
        index < MAP_SNAPSHOTS.length;
        index++
    ) {
        const snapshot =
            MAP_SNAPSHOTS[index]

        if (!snapshot) {
            throw new Error(
                `Missing snapshot at index ${index}`,
            )
        }

        await downloadSnapshot(
            index,
            snapshot,
        )
    }

    console.log(
        `Downloaded ${MAP_SNAPSHOTS.length} snapshots.`,
    )
}

await main()