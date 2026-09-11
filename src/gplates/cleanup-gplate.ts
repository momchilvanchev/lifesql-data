import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname } from 'node:path'
import { featureCollection } from '@turf/helpers'
import { union } from '@turf/union'

const input_path =
    'data/raw/gplates/cao2024/coastlines/24-jurassic-early-188.1Ma.geojson'
const output_path = "data/processed/gplates/cao2024/coastlines/24-jurassic-early-188.1Ma-processed.geojson"
const data =
    JSON.parse(
        await readFile(input_path, 'utf8'),
    )

console.log('input features:', data.features.length)

let result = null
let processed = 0

for (
    const feature of data.features
) {
    if (!result) {
        result = feature
    } else {
        try {
            result =
                union(
                    featureCollection([
                        result,
                        feature,
                    ]),
                )
        } catch (error) {
            console.error(
                `Union failed at feature ${processed}`,
                error,
            )
            break
        }
    }

    processed++

    if (
        processed % 100 === 0
    ) {
        console.log(
            `processed: ${processed}`,
        )
    }
}

if (!result) {
    throw new Error(
        'No geometry produced',
    )
}

console.log(
    'result geometry:',
    result.geometry?.type,
)

console.log(
    'processed:',
    processed,
)

await mkdir(
    dirname(output_path),
    { recursive: true },
)

await writeFile(
    output_path,
    JSON.stringify(result),
)

console.log(
    `wrote: ${output_path}`,
)