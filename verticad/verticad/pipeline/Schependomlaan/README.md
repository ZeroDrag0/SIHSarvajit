# Schependomlaan dataset workspace

This folder is the project-local working area for the Schependomlaan dataset used in the SIH pipeline.

Important constraints:
- Source IFC and point-cloud datasets remain in the archive repository at `../Archive-DataSetSchependomlaan`.
- This workspace avoids duplicating large source data unless a processed derivative is explicitly generated.
- The primary design IFC is treated as the authoritative source for the first IFC-derived 3D unit pipeline.
- Weekly as-planned IFCs are retained for temporal comparison and provenance tracking only.
- Any legal or cadastral conclusions require separate authoritative data sources not present in this repository.

## Local structure

- `raw/` contains reference material and local copies of small metadata files.
- `external/` is reserved for later cadastral/BAG/AHN data placeholders.
- `processed/` contains machine-readable stage outputs from the pipeline.

## Real source references

- Design IFC: `../Archive-DataSetSchependomlaan/Design model IFC/IFC Schependomlaan.ifc`
- As-planned IFCs: `../Archive-DataSetSchependomlaan/As Planned models/`
- Point clouds: `../Archive-DataSetSchependomlaan/Point Clouds/`

The first implementation focuses on `IfcSpace`-based units derived from the actual source IFC and explicitly labels them as `derived/prototype` when legal boundaries are unavailable.

## Status of outputs (see processed/cadastre/pipeline_report.json)

Units are *derived/inferred prototype property units* - not official apartments, not legal cadastral units, ownership unknown.
`processed/_superseded_100_unit_run/` holds the earlier one-unit-per-IfcSpace outputs (wrong; kept for traceability only).


## Real-data run notes (latest)

- IFC: `Design model IFC/IFC Schependomlaan.ifc` (49 MB) from openBIMstandards/Archive-DataSetSchependomlaan, master.
- Point clouds in that repo are **Git LFS objects**. If `Point Clouds/**` files are ~134 bytes they are pointer stubs;
  run `git lfs pull` inside the archive. The inventory reports `git_lfs_pointer_not_downloaded` rather than guessing.
- Point-cloud vs IFC metrics need a registration: `external/pointcloud/registration.json`
  `{"registrations":[{"file_name_contains":"week 27","unit_scale_to_m":1.0,"matrix_4x4":[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],"source":"..."}]}`.
  Without it the result is `not_computed_registration_unverified` (no alignment is invented).
- Flat outputs: `processed/{building,floors,property_units,space_classification,pointcloud_inventory,topology_validation,3d_cadastral_model,ulpins,provenance,pipeline_report}.json`.
- 94 of 100 IfcSpaces have no Body in the IFC; they are extruded from FootPrint+Box and flagged `is_fallback`.
