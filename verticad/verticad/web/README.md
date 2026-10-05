# VERTICAD web

Production-oriented frontend for the VERTICAD 3D cadastral demonstrator. React 19 + TypeScript + Vite, Three.js via @react-three/fiber.

It is frontend only. All data comes from the pipeline's `processed/` outputs; nothing is generated here.

## Run

```
npm install
npm run dev        # http://localhost:5173
npm run build      # type-check + production build into dist/
npm run preview    # serve dist/
npm run lint
```

## Data

Default (static) mode reads the pipeline files copied to `public/data/schependomlaan/`.
After re-running the pipeline, refresh them:

```
npm run sync:data                         # from ../pipeline/Schependomlaan/processed
npm run sync:data -- /path/to/processed   # or any other location
```

To use a backend instead, set `VITE_API_BASE_URL` (see `.env.example`). The frontend then calls
the endpoints below and expects each to return the matching pipeline document unchanged.

| Endpoint | Pipeline output (`processed/`) |
| --- | --- |
| GET /api/building | building.json |
| GET /api/floors | floors.json |
| GET /api/units | property_units.json |
| GET /api/ulpins | ulpins.json |
| GET /api/validation | topology_validation.json |
| GET /api/provenance | provenance.json |
| GET /api/metrics | pipeline_report.json |
| GET /api/pointcloud | pointcloud_inventory.json |
| GET /api/cadastral | 3d_cadastral_model.json |
| GET /api/spaces | space_classification.json |
| GET /api/spaces/geometry | geometry/space_geometry.json (lazy) |
| GET /api/assets/property_units.glb | geometry/property_units.glb |

`/api/data-sources` has no pipeline document; the view is composed in `src/api/dataSources.ts`
from the status fields of the report, provenance, point-cloud and cadastral documents.

## Layout

```
src/api/         one module per endpoint + client.ts (the only place fetch is called)
src/types/       raw.ts (pipeline shapes), domain.ts (UI model)
src/services/    dataset context, selection store, hash router, search index
src/viewer/      Three.js scene, camera rig, floor rail, layer panel
src/components/  inspector, ULPIN panel, badges, states, nav, search
src/pages/       overview, viewer, units, ulpin, validation, data, spatial, pipeline
src/styles/      tokens.css, app.css
scripts/         sync-pipeline-data.mjs (byte-for-byte copy)
```


## Product structure

- **Home** — concise product story and entry point
- **Explore** — lazy-loaded 3D spatial viewer
- **Properties** — building → floor → property explorer
- **Data** — source status, provenance and limitations
- **Validation** — geometry and topology evidence
- **Technology** — implemented capabilities, extensibility and pipeline stages

The interface deliberately uses plain English labels such as **Floor**, **Property**, **3D Survey**, **Ground Elevation**, **Surface Elevation**, **Property Boundary**, and **3D Property ID**. Technical terminology remains available in detail views. Missing inputs are never represented as live data.

The current demonstrator may show a **Prototype 3D ULPIN**. This is not an official government identifier and must not be interpreted as proof of legal ownership.
