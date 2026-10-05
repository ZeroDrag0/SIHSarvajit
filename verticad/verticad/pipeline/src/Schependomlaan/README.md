# Schependomlaan prototype 3D cadastre pipeline

Real IFC -> inspection -> semantic classification -> storeys -> *inferred* vertical property units -> 3D unit
geometry -> point-cloud check -> optional cadastre/terrain/CRS -> 3D topology validation -> prototype 3D ULPIN
-> interoperable 3D cadastral model. Drone imagery is not an input (none exists in this dataset).

    cd <repo root>
    pip install -r src/Schependomlaan/requirements.txt
    PYTHONPATH=src python -m Schependomlaan.run_pipeline --stage all \
        --ifc "<path>/Design model IFC/IFC Schependomlaan.ifc" \
        --pointcloud-dir "<path>/Point Clouds"
    # stages: inspect preprocess classify floors units geometry pointcloud cadastral terrain validate ulpin export all
    PYTHONPATH=src python -m pytest tests -q

Source discovery: --ifc, $SCHEP_IFC, Schependomlaan/raw/ifc/*.ifc, then the archive path in config. If no IFC is
found the pipeline falls back to the cached earlier inspection (`processed/ifc/schependomlaan_inspection.json`) and
says so in every output (`source_mode: cached_legacy_inspection`); geometry stages then report `unavailable` and
topology validation reports `valid: false`.

Optional local inputs (never downloaded): `external/cadastral/*.{geojson,json,gpkg,gml}` (+ optional
`building_parcel_link.json`), `external/bag/`, `external/terrain/*.{tif,asc}`, `external/underground/*.geojson`,
`external/gnss/control_points.csv`. Rules live in `config/rules.yaml`.
