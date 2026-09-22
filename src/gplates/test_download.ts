import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

const BASE_URL =
    'https://gws.gplates.org/reconstruct/static_polygons/'

const MODEL =
    'MULLER2022'

const TIME_MA =
    250

const OUTPUT_DIRECTORY =
    'data/raw/gplates/muller2022/continents'

const OUTPUT_FILE =
    '250Ma.geojson'

async function main() {
    await mkdir(
        OUTPUT_DIRECTORY,
        { recursive: true },
    )

    const url =
        new URL(BASE_URL)

    url.searchParams.set(
        'time',
        String(TIME_MA),
    )

    url.searchParams.set(
        'model',
        MODEL,
    )

    console.log(
        `[download] ${MODEL} @ ${TIME_MA} Ma`,
    )

    const response =
        await fetch(url)

    if (!response.ok) {
        throw new Error(
            `HTTP ${response.status} ${response.statusText}`,
        )
    }

    const text =
        await response.text()

    const outputPath =
        join(
            OUTPUT_DIRECTORY,
            OUTPUT_FILE,
        )

    await writeFile(
        outputPath,
        text,
        'utf8',
    )

    console.log(
        `[saved] ${outputPath} (${text.length.toLocaleString()} bytes)`,
    )
}

await main()