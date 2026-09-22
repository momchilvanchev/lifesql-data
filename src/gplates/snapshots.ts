export type GeologicalMapSnapshot = {
    id: string
    timeMa: number
    period: string
    epoch: string
}

export const MAP_SNAPSHOTS: GeologicalMapSnapshot[] = [
    { id: 'ediacaran', timeMa: 586.9, period: 'Ediacaran', epoch: 'Ediacaran' },

    { id: 'cambrian-terreneuvian', timeMa: 529.9, period: 'Cambrian', epoch: 'Terreneuvian' },
    { id: 'cambrian-series-2', timeMa: 513.3, period: 'Cambrian', epoch: 'Series 2' },
    { id: 'cambrian-miaolingian', timeMa: 501.8, period: 'Cambrian', epoch: 'Miaolingian' },
    { id: 'cambrian-furongian', timeMa: 491.2, period: 'Cambrian', epoch: 'Furongian' },

    { id: 'ordovician-early', timeMa: 477.7, period: 'Ordovician', epoch: 'Early' },
    { id: 'ordovician-middle', timeMa: 464.2, period: 'Ordovician', epoch: 'Middle' },
    { id: 'ordovician-late', timeMa: 451.1, period: 'Ordovician', epoch: 'Late' },

    { id: 'silurian-llandovery', timeMa: 438.6, period: 'Silurian', epoch: 'Llandovery' },
    { id: 'silurian-wenlock', timeMa: 430.4, period: 'Silurian', epoch: 'Wenlock' },
    { id: 'silurian-ludlow', timeMa: 425.2, period: 'Silurian', epoch: 'Ludlow' },
    { id: 'silurian-pridoli', timeMa: 421.3, period: 'Silurian', epoch: 'Pridoli' },

    { id: 'devonian-early', timeMa: 406.5, period: 'Devonian', epoch: 'Early' },
    { id: 'devonian-middle', timeMa: 388.0, period: 'Devonian', epoch: 'Middle' },
    { id: 'devonian-late', timeMa: 370.8, period: 'Devonian', epoch: 'Late' },

    { id: 'carboniferous-mississippian', timeMa: 341.1, period: 'Carboniferous', epoch: 'Mississippian' },
    { id: 'carboniferous-pennsylvanian', timeMa: 311.1, period: 'Carboniferous', epoch: 'Pennsylvanian' },

    { id: 'permian-cisuralian', timeMa: 286.0, period: 'Permian', epoch: 'Cisuralian' },
    { id: 'permian-guadalupian', timeMa: 266.3, period: 'Permian', epoch: 'Guadalupian' },
    { id: 'permian-lopingian', timeMa: 255.7, period: 'Permian', epoch: 'Lopingian' },

    { id: 'triassic-early', timeMa: 249.6, period: 'Triassic', epoch: 'Early' },
    { id: 'triassic-middle', timeMa: 242.1, period: 'Triassic', epoch: 'Middle' },
    { id: 'triassic-late', timeMa: 219.2, period: 'Triassic', epoch: 'Late' },

    { id: 'jurassic-early', timeMa: 188.1, period: 'Jurassic', epoch: 'Early' },
    { id: 'jurassic-middle', timeMa: 168.1, period: 'Jurassic', epoch: 'Middle' },
    { id: 'jurassic-late', timeMa: 153.3, period: 'Jurassic', epoch: 'Late' },

    { id: 'cretaceous-early', timeMa: 122.8, period: 'Cretaceous', epoch: 'Early' },
    { id: 'cretaceous-late', timeMa: 83.3, period: 'Cretaceous', epoch: 'Late' },

    { id: 'paleogene-paleocene', timeMa: 61.0, period: 'Paleogene', epoch: 'Paleocene' },
    { id: 'paleogene-eocene', timeMa: 45.0, period: 'Paleogene', epoch: 'Eocene' },
    { id: 'paleogene-oligocene', timeMa: 28.5, period: 'Paleogene', epoch: 'Oligocene' },

    { id: 'neogene-miocene', timeMa: 14.2, period: 'Neogene', epoch: 'Miocene' },
    { id: 'neogene-pliocene', timeMa: 4.0, period: 'Neogene', epoch: 'Pliocene' },

    { id: 'quaternary-pleistocene', timeMa: 1.3, period: 'Quaternary', epoch: 'Pleistocene' },
    { id: 'quaternary-holocene', timeMa: 0, period: 'Quaternary', epoch: 'Holocene' },
];
