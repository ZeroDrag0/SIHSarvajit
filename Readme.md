from pathlib import Path
import zipfile, os, textwrap

readme = r'''# VERTICAD — 3D Vertical Cadastre

> Transforming conventional 2D building representations into structured, searchable and validated 3D vertical cadastral information.

**Smart India Hackathon 2026 · SIH26011**

---

## Overview

Traditional cadastral and property datasets primarily represent buildings as two-dimensional footprints. However, modern urban properties are inherently vertical — buildings contain multiple floors, individual units and property-level spatial relationships.

This project explores a **3D Vertical Cadastre** framework that represents the built environment across multiple spatial levels:

```text
2D Building Footprint
        ↓
Geospatial Processing
        ↓
3D Building Reconstruction
        ↓
Floor Decomposition
        ↓
Property / Unit Partitioning
        ↓
Property Identifier / ULPIN
        ↓
Geometry & Topology Validation
        ↓
Interactive 3D Cadastre
```

The current repository contains the **high-fidelity frontend prototype** for this system.

---

## Key Objectives

- Represent buildings as structured 3D spatial entities.
- Move from building-level footprints toward floor- and unit-level representation.
- Enable interactive exploration of vertical property structures.
- Associate property units with unique identifiers such as ULPIN.
- Provide geometry, topology and identifier validation.
- Maintain traceability between derived cadastral objects and their source data.
- Provide a foundation for integrating geospatial processing and backend cadastral services.

---

## Current Prototype

The current frontend demonstrates the proposed user experience through a Bengaluru case study:

### Prestige Kingfisher Towers

The prototype demonstrates:

- 3D building visualization
- Floor-level exploration
- Unit-level property representation
- ULPIN prototype identifiers
- Geometry validation indicators
- Property information panels
- GIS-style map visualization
- Building/property search interface
- Cadastral pipeline visualization
- Data provenance concepts

### Demonstration Dataset

| Parameter | Prototype Value |
|---|---:|
| Building | Prestige Kingfisher Towers |
| Location | Bengaluru, Karnataka |
| Floors | 34 |
| Generated Units | 136 |
| Units / Floor | 4 |
| ULPIN Prototypes | 136 |
| Geometry Linkage | 100% |
| Duplicate Identifier Check | 0 detected |
| Overlap | 0 m² |
| Uncovered Area | 0 m² |
| Derived Height | 120 m |

> **Important:** These values represent prototype/demo outputs and should not be interpreted as legally surveyed cadastral measurements or official property records.

---

## System Architecture

The current repository represents the presentation and visualization layer of the larger proposed system.

```text
                 ┌─────────────────────────┐
                 │     User / Operator      │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │     React Frontend       │
                 │  Search / Map / 3D UI   │
                 └────────────┬────────────┘
                              │
                         API Layer
                              │
                 ┌────────────▼────────────┐
                 │     Cadastral Backend   │
                 │          (Planned)      │
                 └────────────┬────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    Geospatial Data       3D Models          Validation
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                  Building / Floor / Unit
                  / Identifier Information
```

The backend/API and persistent geospatial database are part of the planned integration architecture and are not currently implemented in this frontend repository.

---

## Technology Stack

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS

### Visualization

- Three.js
- React Three Fiber
- React Three Drei
- SVG-based geospatial visualizations

### Planned Geospatial / Backend Stack

The following components are intended for subsequent implementation:

- Python
- FastAPI
- PostgreSQL
- PostGIS
- GDAL / Rasterio
- GeoPandas
- 3D geospatial processing
- REST APIs

---

## Core User Flow

```text
Landing Page
     ↓
Search Building / Locality / ULPIN
     ↓
Building Result
     ↓
Open 3D Building
     ↓
Select Floor
     ↓
Select Property Unit
     ↓
View Property Information
     ↓
Inspect Identifier & Validation
```

The goal is to make the system behave like a **property discovery platform combined with a professional GIS environment**, rather than a static 3D visualization.

---

## Cadastral Data Hierarchy

```text
City
 └── Locality
      └── Building
           ├── Floor 01
           │    ├── Unit 01
           │    ├── Unit 02
           │    └── ...
           ├── Floor 02
           │    ├── Unit 01
           │    └── ...
           └── Floor N
```

Each spatial entity can maintain relationships with:

- Parent geometry
- Child geometries
- Spatial coordinates
- Area
- Floor information
- Property identifier
- Source/provenance information
- Validation status

---

## Validation Framework

### Geometry Validation

Checks whether generated spatial geometries are valid.

### Topology Validation

Checks for:

- overlapping units
- gaps
- invalid boundaries
- inconsistent spatial relationships

### Identifier Validation

Checks:

- uniqueness
- duplicate identifiers
- building-to-unit linkage
- unit-to-identifier mapping

### Provenance

Maintains information about how a cadastral object was derived from its source data.

---

## AI / Computational Components

The system is designed as an **AI-assisted geospatial pipeline**, rather than treating every component as AI.

### AI / ML

Potential applications include:

- building extraction
- spatial feature interpretation
- property structure inference
- automated geospatial analysis

### Geospatial Processing

- coordinate transformation
- geometry processing
- spatial relationships
- GIS operations

### Procedural Reconstruction

- 3D building generation
- floor decomposition
- unit-level spatial structuring

### Rule-Based Validation

- topology checks
- identifier validation
- consistency checks
- provenance verification

---

## Current Status

### Implemented

- [x] High-fidelity landing page
- [x] Property/building search interface
- [x] GIS-inspired interface
- [x] 3D cadastral visualization concept
- [x] Building/floor/unit information hierarchy
- [x] ULPIN prototype representation
- [x] Validation dashboard concept
- [x] Bengaluru demonstration case study

### In Development

- [ ] FastAPI backend
- [ ] PostgreSQL/PostGIS database
- [ ] REST API
- [ ] Persistent cadastral data model
- [ ] Automated geospatial processing pipeline
- [ ] Real building footprint ingestion
- [ ] Automated 3D reconstruction
- [ ] Automated floor/unit extraction
- [ ] Production-grade ULPIN integration
- [ ] Scalable multi-building deployment

---

## Roadmap

```text
Phase 1
High-Fidelity Prototype
        ↓
Phase 2
Geospatial Data Pipeline
        ↓
Phase 3
3D Reconstruction
        ↓
Phase 4
Cadastral Database + API
        ↓
Phase 5
Automated Validation
        ↓
Phase 6
Multi-Building / City-Scale Deployment
```

---

## Demonstration Scope

The current demonstration focuses on **Prestige Kingfisher Towers, Bengaluru** as a representative high-rise building.

The case study demonstrates the vertical cadastral workflow and user experience.

It should not be interpreted as an official cadastral survey or government-certified property database.

---

## Recommended Repository Images

Place screenshots in:

```text
docs/
└── images/
    ├── hero.png
    ├── architecture.png
    ├── building-viewer.png
    ├── floor-unit-explorer.png
    ├── validation.png
    └── system-overview.png
```

Recommended screenshots:

1. **hero.png** — Landing page
2. **architecture.png** — End-to-end system architecture
3. **building-viewer.png** — 3D Kingfisher Towers viewer
4. **floor-unit-explorer.png** — Floor and unit selection
5. **validation.png** — Geometry/topology/identifier validation
6. **system-overview.png** — Complete map + building + property information workflow

Use screenshots from the actual working prototype rather than stock or AI-generated visuals.

---

## Running Locally

### Prerequisites

- Node.js 18+
- pnpm

### Installation

```bash
git clone <repository-url>
cd <repository-name>
pnpm install
```

### Development Server

```bash
pnpm dev
```

### Production Build

```bash
pnpm build
```

---

## Project Context

This project is being developed for:

**Smart India Hackathon 2026**

**Problem Statement: SIH26011**

The objective is to explore a practical framework for representing and managing **vertical cadastral information** in increasingly dense urban environments.

---

## Disclaimer

This repository contains a research/prototype implementation.

The building geometry, floor decomposition, unit partitions and ULPIN values shown in the current demonstration may include derived or synthetic prototype data.

They do not constitute:

- official cadastral records
- legal property boundaries
- government-certified ULPIN records
- ownership verification
- legal survey measurements

Production deployment would require authoritative datasets, appropriate government validation, legal compliance and integration with official cadastral systems.

---

## Team

**SIH 2026 Team**

Developed as part of the Smart India Hackathon 2026.

---

## License

This project is currently intended for academic and hackathon demonstration purposes.

Add an explicit open-source license if the team decides to publish the source under one.
'''

out = "/mnt/data/README.md"
Path(out).write_text(readme, encoding="utf-8")

zip_out = "/mnt/data/3D_Vertical_Cadastre_README.zip"
with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(out, "README.md")

print(zip_out)