> **QGIS Live Harness のプラグイン** — [QGIS Live Harness](https://yamamoto-ryuzo.github.io/qgis_live_harness/) · [プラグイン一覧](https://yamamoto-ryuzo.github.io/qgis_live_harness/plugins.html) · [リポジトリ](https://github.com/yamamoto-ryuzo/qgis_live_harness)

# geo_webview — Feed web map clients serverlessly, and turn QGIS into an OGC server

[日本語版はこちら / Japanese: `README_JP.md`](README_JP.md)

> Part of the `geo_suite` project — a lightweight QGIS plugin that delivers a QGIS project to web map clients in two ways: serverless file export, and a WMS/WMTS/WFS OGC-compliant server.

## Overview

`geo_webview` connects QGIS and the Web. QGIS is the ideal environment for working with GIS data; this plugin turns QGIS into the **serving side** and delivers data to various web map clients through two complementary services:

### Serverless delivery (file export)

Writes a `.kasc` + `DATA/` package (layer tree, `.qml` styles, `cam:` view state) to a specified folder. `.kasc` is the KASUGAI Canvas project format — once exported it runs without the QGIS-side server, and the `.kasc`+`DATA/`+system bundle can be cut out and distributed as a unit. A `reearth.txt` for Re:Earth Visualizer can also be emitted.

Engine launcher pages (`cesium.html`/`maplibre.html`/`openlayers.html`/`leaflet.html`) plus an `index.html` link list are written next to the `.kasc`. Each HTML redirects to its engine with `?kasc=<this .kasc URL>` and auto-detects the engine (`./ ../ ../../ /` in order; set `CANVAS_BASE` inside the HTML for custom layouts). **Uploading the export folder together with the engine (`web/` contents) to the same static host gives you a serverless standalone web delivery** (Canvas's `?kasc=` direct-load mode).

The player system itself is **maintained in KASUGAI Canvas** — a multi-engine app (Cesium / MapLibre / OpenLayers / Leaflet; the web part runs on static hosting, the EXE side provides rclone, auto-update, file saving, `.kasc` association). The intended flow is registering the KASUGAI install location and writing `.kasc`+`DATA/` into its `QGIS_projects/` directory (a dedicated folder, separate from Canvas's own `projects/`). The plugin's built-in generated viewers (former `/qgis-map`, `/maplibre`, `/map3d`) were removed in v3.24.0 — viewing is fully consolidated into KASUGAI Canvas.

KASUGAI Canvas-side layout (`web/`):

```
web/
  index.html      engine-select redirect (?engine=cesium|maplibre|openlayers|leaflet, default cesium)
  cesium/         Cesium front (current app)
  maplibre/       MapLibre front (.kasc player implemented: all vector lines, wms:/wmts:, QML, duckdb/sql, attribute UI, 6-tab panel)
  openlayers/     OpenLayers front (same)
  shared/         engine-independent core (.kasc loader, decoders, i18n, QML compilers)
  projects/       project data (engine-independent)
    projects.json          project list manifest
    DATA/                  (optional) data shared by all projects (../DATA/ refs)
    <id>/                  project (multiple, keyed by id)
      kasugai_canvas.kasc  project settings
      DATA/                project-local data
```

The `.kasc`+`DATA/` geo_webview exports lands as one `projects/<id>/` project, and relative references inside `.kasc` lines resolve against `projects/<id>/`.

### OGC-compliant server

A **general-purpose** built-in HTTP server that publishes the open QGIS project as standard OGC services (WMS 1.3.0 / WMTS / XYZ / WFS 2.0). It acts as the backend resolving live references inside data packages (`xyz:`/WMTS tiles, `/wfs` GeoJSON, `/export-data/`). Being standard OGC, the same endpoints work for any external OGC client (QGIS, ArcGIS, other WebGIS).

No complex server setup is required: open a QGIS project and both delivery paths are available immediately.

Typical uses:
- Sharing internal map data on a LAN
- Delivering data to mobile field apps
- Quickly standing up an emergency map server
- Packaging a QGIS project as a distributable map service

![Panel screenshot](images/image01.png)

## Integration policy (supported clients)

geo_webview's integration policy consolidates the player into **KASUGAI Canvas** — a multi-engine setup (Cesium + OpenLayers/MapLibre/Leaflet fronts, implemented on the KASUGAI side; switch via `?engine=`) — with **Re:Earth Visualizer as secondary**. Everything else is served through generic OGC output.

### ① Companion players developed alongside geo_webview

Clients that ingest data & styles exported/served from QGIS and play them as independent WebGIS. geo_webview is being developed as the QGIS-side delivery backend for these players.

| Target | Route | Integration |
|---|---|---|
| **KASUGAI Canvas** | `/kasugai` (`.kasc`+`DATA/`) | **Unified player (primary).** A standalone WebGIS app — geo_webview writes the QGIS layer tree as `.kasc`+`DATA/` (vectors + `.qml` styles) and registers it with a running KASUGAI local server, then switches the view. The panel `Export` button writes the project files only (incl. `index.html` + per-engine launcher HTMLs); `GET /kasugai?engine=` or the `kasugaiExport` bridge also registers and launches a given engine — the same `.kasc`+`DATA/` plays on every engine. An EXE-installed copy also provides rclone, auto-update, file saving and `.kasc` association |
| **Re:Earth Visualizer (geo_suite)** | `reearth.txt` export + generic OGC output | **Secondary** (Cesium-based like KASUGAI Canvas). `reearth.txt` inspector text plus `/wfs` GeoJSON, `/xyz`/`/wmts` tiles and `.qml` styles are consumed client-side (geo_suite ships a QML→Re:Earth translator) |
Note: 3D work is consolidated in the Cesium-based clients — KASUGAI Canvas (primary) and Re:Earth Visualizer (secondary).

### ② Other clients & external services

| Target | Route | Integration |
|---|---|---|
| **Other OGC clients** | `/wms` `/wmts` `/xyz` `/wfs` | Any client that speaks WMS 1.3.0 / WMTS / XYZ / WFS 2.0 (QGIS, ArcGIS, web apps, ...) |
| **Google Maps / Google Earth** | URL generation & parsing | Generates Google Maps/Earth URLs from the current view and opens them in a browser; received Google URLs are parsed into QGIS navigation via External Control |

### Integration architecture (development direction)

The combination above is the development direction going forward.

```mermaid
flowchart LR
    QGIS["QGIS project<br>layers / styles / view state"]
    GW["geo_webview<br>WMS / WMTS・XYZ / WFS<br>viewer generation / export"]

    subgraph G1["① Companion players (co-developed)"]
        direction TB
        subgraph G1_UNI["Unified players"]
            KC["KASUGAI Canvas (primary)<br>Cesium/OL/MapLibre/Leaflet multi-engine"]
            RE["Re:Earth Visualizer geo_suite (secondary)"]
        end
    end

    subgraph G2["② Other clients & external services"]
        OC["Generic OGC clients"]
        GM["Google Maps / Earth"]
    end

    QGIS --> GW
    GW -->|"/kasugai (.kasc+DATA/)"| KC
    GW -->|"/wfs・/xyz・.qml"| RE
    GW -->|"/wms・/wmts・/xyz・/wfs"| OC
    GW -->|"URL generation / parsing"| GM
```

Note: Leaflet is also available as a KASUGAI Canvas engine (`?engine=leaflet`; functionally a subset of the OpenLayers engine — no rotation/arbitrary CRS).

## Features of the client group

The matrix below inventories what each group-① client can do, organized around **KASUGAI Canvas** — the most developed client — as the reference axis. `—` = no equivalent, `△` = partial. The QGIS-side services that feed these clients are listed at the end.

### Data ingestion & layer formats

Clients fall into two ingestion types: **declared (file-specified)** — the client itself decodes a file in the specified format given as a local path or URL (KASUGAI Canvas `.kasc` lines like `gpkg:DATA/x.gpkg` on every engine, Re:Earth inspector lines like `geojson: URL`) — and **served (protocol-defined)**, where the server picks the format and delivers it via an OGC protocol (any MapLibre/OpenLayers client: vectors via `/wfs` GeoJSON, rasters as WMS/WMTS renders).

| Feature | KASUGAI Canvas | Re:Earth geo_suite | MapLibre (Canvas engine) | OpenLayers (Canvas engine) |
|---|:-:|:-:|:-:|:-:|
| Ingestion route | `.kasc` + `DATA/` files (`/kasugai` export + `/api/projects/register`) | `reearth.txt` inspector export (`/kasugai` output, when HTTP server running); `/wfs` GeoJSON, `/xyz`, `.qml`, `/export-data/` files; Manage-tab file import | `.kasc` lines + local files (.geojson/.fgb/.parquet/.gpkg/.csv/.tsv/.kasc) | same as MapLibre |
| GeoJSON | ✓ (`geojson:`) | ✓ (`geojson:`) | ✓ (`geojson:` / file) | ✓ (`geojson:` / file) |
| GeoPackage | ✓ (`gpkg:` Worker, `bbox=auto` query) | ✓ (`gpkg:` sql.js, `bbox=auto`, embedded `layer_styles` QML) | ✓ (`gpkg:` sql.js Worker, `bbox=auto`) | ✓ (`gpkg:` sql.js Worker, `bbox=auto`) |
| GeoParquet | ✓ (`geoparquet:`) | ✓ (`parquet:` / `geoparquet:`) | ✓ (`geoparquet:` hyparquet) | ✓ (`geoparquet:` hyparquet) |
| FlatGeobuf | ✓ (`flatgeobuf:`) | ✓ (`flatgeobuf:` / `fgb:`) | ✓ (`flatgeobuf:` / `fgb:`) | ✓ (`flatgeobuf:` / `fgb:`) |
| CSV / TSV | ✓ (`duckdb:` + `format=csv`, `lon=`/`lat=`/`geom=`) | ✓ (`duckdb:` + file import lon/lat) | ✓ (`duckdb:` + `format=csv`; file import lon/lat) | ✓ (same) |
| DuckDB / SQL query layers | ✓ (`duckdb:` / `sql:`, `:bbox` viewport re-query) | ✓ (`duckdb:` / `sql:`, DuckDB-Wasm, `:bbox` re-query) | ✓ (`duckdb:` / `sql:`, `:bbox` viewport re-query) | ✓ (same) |
| Layer filter (`subsetString`) | ✓ (`where=` on `gpkg:`/`duckdb:`, or baked into GeoJSON) | ✓ (same — `where=` or baked) | ✓ (`where=` on `gpkg:`/`duckdb:`) | ✓ (same) |
| 3D Tiles | ✓ (`3dtiles:`) | ✓ (`3dtiles:`) | — (reported as unsupported) | — (same) |
| XYZ tiles / basemap | ✓ (`xyz:` / `base:`) | ✓ (`xyz:` / `tile:` / `base:`, basemap widget) | ✓ (`xyz:` / `base:` overlay) | ✓ (`xyz:` / `base:` overlay) |
| WMS / WMTS rasters | ✓ (`wms:` / `wmts:` — GetMap tiled into 256 px / `{z}/{x}/{y}` & KVP GetTile normalization) | — | ✓ (`wms:` / `wmts:` lines via Import panel) | ✓ (same) |
| QGIS style (.qml) | ✓ (`style=`, compiled client-side to entity/primitive) | ✓ (QML→Re:Earth translator, incl. GPKG `layer_styles`) | — (default styling) | — (default styling) |

**Served (protocol-defined)**: the server chooses the format and delivers it via an OGC protocol — MapLibre and OpenLayers; the client only receives what it is given. Any source QGIS loads as a vector layer is covered via `/wfs` GeoJSON; everything visible is covered via the raster service.

| Feature | KASUGAI Canvas | Re:Earth geo_suite | MapLibre | OpenLayers |
|---|:-:|:-:|:-:|:-:|
| Ingestion route | — | — | WMTS/WMS raster + `/wfs` GeoJSON (`wms:`/`wmts:` lines; external MapLibre clients use `/maplibre-style`) | `/wms` raster |
| GeoJSON | — | — | ✓ (`/wfs`) | △ (WMS raster render + GetFeatureInfo) |
| GeoPackage | — | — | ✓ (`/wfs` GeoJSON) | △ (WMS raster) |
| GeoParquet | — | — | ✓ (`/wfs` GeoJSON) | △ (WMS raster) |
| FlatGeobuf | — | — | ✓ (`/wfs` GeoJSON) | △ (WMS raster) |
| CSV / TSV | — | — | ✓ (`/wfs` GeoJSON) | △ (WMS raster) |
| DuckDB / SQL query layers | — | — | — | — |
| Layer filter (`subsetString`) | — | — | ✓ (reflected in `/wfs` output) | ✓ (reflected in WMS render) |
| 3D Tiles | — | — | — | △ (WMS raster render) |
| XYZ tiles / basemap | — | — | ✓ (XYZ / WMTS sources) | ✓ (WMS render) |
| QGIS style (.qml) | — | — | ✓ (`/maplibre-style` auto-convert) | ✓ (WMS server-side render) |

### Layer management & display

| Feature | KASUGAI Canvas | Re:Earth geo_suite | MapLibre | OpenLayers |
|---|:-:|:-:|:-:|:-:|
| Layer list UI | ✓ | ✓ (layers-and-tiles-list) | ✓ | — |
| Groups (inherits layer tree) | ✓ | ✓ (group rules) | △ | — |
| Visibility on/off | ✓ | ✓ | ✓ | — |
| Legend | ✓ | ✓ | — | — |
| SQL filter / interactive re-query | ✓ | — | — | — |
| Render mode (`render=entity/primitive`) | ✓ | — | — | — |

### Search & attributes

| Feature | KASUGAI Canvas | Re:Earth geo_suite | MapLibre | OpenLayers |
|---|:-:|:-:|:-:|:-:|
| Address search | ✓ | ✓ | — | — |
| Vector search | ✓ | ✓ | — | — |
| Attribute / value list | ✓ (Attr panel, full-table query) | ✓ | — | △ (GetFeatureInfo) |
| Info display | ✓ | ✓ | — | — |

### View & navigation

| Feature | KASUGAI Canvas | Re:Earth geo_suite | MapLibre | OpenLayers |
|---|:-:|:-:|:-:|:-:|
| View handoff | `cam:` line in `.kasc` | `?lat=&lng=` query | `x,y,scale,rotation` | `x,y,scale,rotation,crs` |
| Rotation | ✓ (heading) | △ | ✓ | ✓ |
| Arbitrary CRS | — | — | — | ✓ |
| Map themes | ✓ (`theme:` lines + layer-panel select, visibility presets) | — | ✓ | ✓ |
| Camera presets / bookmarks | ✓ | ✓ | ✓ | — |
| Terrain / Shadow | ✓ | ✓ | — | — |
| GeoJSON 3D drape | ✓ (terrain / 3D Tiles / both) | ✓ | — | — |
| Follow mode (tracks QGIS canvas) | — | — | ✓ (`/present/state`) | ✓ |

### Presentation, sharing & external services

| Feature | KASUGAI Canvas | Re:Earth geo_suite | MapLibre | OpenLayers |
|---|:-:|:-:|:-:|:-:|
| Fly mode / route drawing | ✓ | ✓ | — | — |
| Permalink / share | ✓ (`buildShareUrl`) | ✓ (query string only) | ✓ | ✓ |
| Bidirectional nav (`/received`, External Control) | — | — | ✓ | ✓ |
| Google integration | ✓ (Google Maps Platform, Photorealistic 3D Tiles) | ✓ (Google Earth link) | — | ✓ (URL generation/parsing) |
| Screen-share presentation | — | — | — | ✓ (`/present`, `/screenshot`) |

### AI, extensibility & local integration

| Feature | KASUGAI Canvas | Re:Earth geo_suite | MapLibre | OpenLayers |
|---|:-:|:-:|:-:|:-:|
| AI chat | ✓ (Gemini function calling, shared tool executor) | ✓ | — | — |
| External agent control | ✓ (`/api/command` + bridge hub → Copilot/Devin/Antigravity) | — | — | △ (Live Driver `kasugaiExport` bridge) |
| MCP data sources | ✓ (`/api/mcp` relay) | — | — | — |
| Plugin system | ✓ (`PLUGIN/`, IndexedDB drafts, `.kasp`) | (is itself a Re:Earth plugin) | — | — |
| Cloud storage (rclone) | ✓ | — | — | — |
| Local save / delivery localization | ✓ (`/api/files`, `_local` workspace) | — | — | — |
| External project registration | ✓ (`.kasc` association, group manifests) | — | — | — |
| i18n | 8 languages | 20 languages | — | — |

### Common QGIS-side services

Features geo_webview provides uniformly to feed the clients above. Per-client differences are only the ingestion route and representation format — the QGIS-side services are shared.

| Common service | KASUGAI Canvas | Re:Earth | MapLibre | OpenLayers |
|---|:-:|:-:|:-:|:-:|
| View handoff (center / scale / rotation) | ✓ (`cam:`) | △ (lat/lng) | ✓ | ✓ |
| Raster delivery (WMS / WMTS / XYZ) | `xyz:`/`base:` | XYZ | WMTS | WMS |
| Vector data | `DATA/` files (native ref or GeoJSON) | WFS/GeoJSON | WFS | — |
| QGIS style handoff | `.qml` (+ GPKG `layer_styles`) | `.qml` | Auto-convert | WMS render |
| Layer list & visibility | ✓ (on/off, groups) | ✓ | ✓ | — |
| Query-layer descriptors (`duckdb:`/`sql:`/`bbox=auto`) | — (not yet exported) | — | — | — |
| Map themes | ✓ (`theme:` lines + layer-panel select, visibility presets) | — | ✓ | ✓ |
| Follow mode (`/present/state`) | — | — | ✓ | ✓ |
| Project registration & view switch | ✓ (`/api/projects/register` + `switchProject`) | — | — | — |

- **View handoff**: reproduces the specified view (`x,y,scale,rotation,crs`, `lat,lon,zoom`, or a permalink) in each client. For KASUGAI it is written as the `.kasc` `cam:` line
- **Raster delivery**: the map exactly as rendered by QGIS via WMS (`ANGLE` rotation supported) / WMTS / XYZ — used as base or overlay by each client
- **Vector data**: published layers (`WFSLayers`) served as GeoJSON — MapLibre & Re:Earth via `/wfs`, KASUGAI as files under `DATA/` (GPKG/GeoJSON/GeoParquet/FlatGeobuf are referenced natively without conversion)
- **Style handoff**: QGIS renderers converted per client — pixel-perfect via server-side WMS/tile rendering, `/maplibre-style` layer conversion for MapLibre, `.qml` files compiled client-side for KASUGAI & Re:Earth
- **Layer list & visibility**: `/wfs-layers` (JSON) is the common layer catalog; KASUGAI also inherits the layer-tree groups and on/off states
- **Query-layer descriptors**: `/kasugai` emits KASUGAI Canvas query types where sources allow it — CSV/TSV (delimitedtext/ogr) as `duckdb:` (`format=`/`lon=`/`lat=`/`geom=`), filtered GPKG as `gpkg:` + `where=`, filtered Parquet as `duckdb:` + `format=parquet` + `where=`. `sql:` (arbitrary SELECT) is not emitted since QGIS has no equivalent source. 3D Tiles layers (`QgsTiledSceneLayer`) are emitted as `3dtiles:`, and local XYZ templates (`file:///…/{z}/{x}/{y}.png`) are copied to `DATA/` as local tile trees. QGIS WMS raster layers (non-`type=xyz`) are emitted as `wms:` lines (with `layers=`/`styles=`/`format=` options) — Canvas tiles GetMap into 256 px requests. `wmts:` lines (`{TileMatrix}` RESTful templates and KVP GetTile) are readable by Canvas and the generated viewers too (geo_webview itself does not emit `wmts:`)
- **Follow mode**: Canvas pages opened with `?follow`/`?present` (MapLibre/OpenLayers/Leaflet engines) poll `/present/state` and track the QGIS canvas in real time (presentation / screen-share)
- **Bidirectional navigation**: permalink ingestion (`/received`) plus External Control also share the view client→QGIS. The reverse path from KASUGAI is the `qgis-import` plugin, which calls `/kasugai` (import only — edits made in Canvas are not sent back to QGIS)

## Integration with geo_suite

`geo_webview` is developed as part of the `geo_suite` project.

- **geo_webview**: run QGIS as an OGC server (this plugin)
- **geo_suite**: client plugin running on Re:Earth Visualizer (viewing & editing)
- **Scenario**: QGIS + `geo_webview` serve data; `geo_suite` consumes it on mobile/desktop

Together they let you package a QGIS project into a distributable system for end users.

## System requirements

- QGIS 3.x (Qt5/Qt6 compatible)
- Windows / macOS / Linux
- Python 3.7+
- Network: local network or localhost

## Main features

### 🗺️ Built-in web pages

The server generates and serves the HTML itself — just open the URL (map viewing itself is handled by KASUGAI Canvas).

| Endpoint | Content |
|---|---|
| `/present` | Presentation page that window-shares the QGIS canvas via periodic `/screenshot` |
| `/screenshot` | PNG of the current canvas (rotation applied; `w`/`h` size params) |

### 🌐 OGC services

#### WMS
- Serve a QGIS project as WMS 1.3.0
- `GetCapabilities` / `GetMap` / `GetFeatureInfo`
- Custom styles (SLD), `theme` parameter, `ANGLE` rotation support
- High-resolution image output (clamped, up to 4096 px)

#### WMTS / XYZ
- Tile delivery via `/wmts/{z}/{x}/{y}.png` and `/xyz/{z}/{x}/{y}.png`
- `GetCapabilities` supported; `tms=1` for TMS (flipped-Y) compatibility
- Identity-based cache separation (`?v=` for client-side cache busting)

#### WFS 2.0
- Vector data as GeoJSON / GML
- `GetCapabilities` / `GetFeature` / `DescribeFeatureType` / `GetStyles` (SLD)
- High-performance cache: repeated requests are dramatically faster

### 🔗 External app integrations

#### KASUGAI Canvas (Cesium / OpenLayers / MapLibre / Leaflet)
- The panel `Export` button exports visible layers as a KASUGAI Canvas project (`.kasc` + `DATA/` + `index.html` and per-engine launcher HTMLs) without launching; `GET /kasugai?engine=<e>` or the `kasugaiExport` bridge also registers the project and launches that engine
- GPKG/GeoJSON/GeoParquet/FlatGeobuf referenced natively; other vectors converted to GeoJSON (EPSG:4326). Each layer's QGIS style is exported as `.qml`. WMS rasters are exported as `wms:` reference lines (`layers=`/`styles=`/`format=`)
- The exported `.kasc`+`DATA/` plays on every engine (`?engine=cesium|openlayers|maplibre|leaflet`) — all 2D line types incl. `wms:`/`wmts:` are supported
- Registers the project with a running KASUGAI local server and switches its view
- Callable the other way from KASUGAI's `qgis-import` plugin (bidirectional)
- Controllable by AI via the `kasugaiExport` bridge through Live Driver (`engine` arg supported)

### 🔄 Permalinks & External Control

- Share the current map view (coordinates, scale, rotation, theme, layer state) as a URL
- With `External Control` enabled, received URLs automatically navigate the QGIS canvas
- Embed links in Office documents (Excel / PowerPoint); export high-resolution PNGs
- Google Maps / Google Earth: generate Google URLs from the current view and open in a browser; received Google URLs are parsed for navigation through the same mechanism (an example of external service integration)

### 📡 Network features (v3.5.0)

- External access diagnostics and firewall detection
- Automatic port configuration (Windows firewall rules helper)
- Flexible port range (supports 80–65535)
- Dynamic hostname resolution for external clients

### 🚀 Performance optimizations

WFS response cache (v3.4.0):

```
First request: 200ms → 70ms (3x faster)
Subsequent requests: 200ms → <5ms (≈40x faster)
1000 features: 1.5s → 500ms
10000 features: 15s → 5s
```

## Quick start

### 1) Install

Place the plugin in your QGIS plugins folder, or install via the QGIS plugin manager.

Windows example path:

```
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\geo_webview
```

### 2) Basic usage

1. Open a QGIS project (.qgs/.qgz)
2. Select `Web > geo_webview` from the menu
3. The panel appears and an HTTP server starts automatically
4. Open the provided URL (e.g. `http://localhost:8089`)

### 3) Example OGC requests

WMS:

```
# GetCapabilities
http://localhost:8089/wms?SERVICE=WMS&REQUEST=GetCapabilities

# GetMap (example)
http://localhost:8089/wms?SERVICE=WMS&REQUEST=GetMap&LAYERS=mylayer&WIDTH=800&HEIGHT=600&BBOX=...
```

WMTS / XYZ:

```
# XYZ tile
http://localhost:8089/wmts/{z}/{x}/{y}.png

# GetCapabilities
http://localhost:8089/wmts?SERVICE=WMTS&REQUEST=GetCapabilities
```

WFS:

```
# GetCapabilities
http://localhost:8089/wfs?SERVICE=WFS&REQUEST=GetCapabilities

# GetFeature (GeoJSON)
http://localhost:8089/wfs?SERVICE=WFS&REQUEST=GetFeature&TYPENAME=mylayer&OUTPUTFORMAT=application/json
```

## Endpoint reference

| Path | Type | Content |
|---|---|---|
| `/maplibre-style` | JSON | MapLibre style (`?typename=` per layer) |
| `/present` | HTML | Presentation window-share page |
| `/screenshot` | PNG | Current canvas image |
| `/wms` | OGC | WMS 1.3.0 (GetCapabilities/GetMap/GetFeatureInfo) |
| `/wmts/{z}/{x}/{y}.png` | OGC | WMTS tile (GetCapabilities via `/wmts?...`) |
| `/xyz/{z}/{x}/{y}.png` | OGC | XYZ tile (WMTS alias) |
| `/wfs` | OGC | WFS 2.0 (GeoJSON/GML) |
| `/wfs-layers` | JSON | Published WFS layer list |
| `/kasugai` | JSON | Export & register to KASUGAI Canvas (`?engine=` selects the launch engine) |
| `/received` | HTML | Received permalink history |

## Common use cases

### Field data collection

Serve QGIS data to mobile field teams via `geo_suite`.

### Internal map portal

Share project views on your LAN (OGC services): `http://192.168.1.100:8089/wms?SERVICE=WMS&REQUEST=GetCapabilities`

### Emergency map server

Quickly publish an existing QGIS project as a temporary server for disaster response.

### Distributable project package

Bundle QGIS Portable + `geo_webview` + data on a USB drive for easy distribution.

### 3D visualization & presentations

Hand off to KASUGAI Canvas (the primary 3D GIS target) via `/kasugai` for 3D review and presentation material, or share the QGIS view on a meeting screen via `/present`.

## WFS details

Supported operations:

| Operation | Description | Output |
|---|---|---|
| GetCapabilities | Service & layer listing | XML |
| GetFeature | Retrieve features | GeoJSON / GML |
| DescribeFeatureType | Feature schema | XML |
| GetStyles | Style (SLD) | XML |

Parameters (examples):

```
SERVICE=WFS
REQUEST=GetFeature
VERSION=2.0.0
TYPENAME=layer_name
OUTPUTFORMAT=application/json
MAXFEATURES=100
BBOX=minx,miny,maxx,maxy
SRSNAME=EPSG:4326
```

Example usage (curl):

```
curl "http://localhost:8089/wfs?SERVICE=WFS&REQUEST=GetCapabilities"
curl "http://localhost:8089/wfs?SERVICE=WFS&REQUEST=GetFeature&TYPENAME=roads&OUTPUTFORMAT=application/json"
curl "http://localhost:8089/wfs?SERVICE=WFS&REQUEST=GetFeature&TYPENAME=buildings&BBOX=130,30,140,40"
```

## MapLibre integration

### Style conversion

QGIS renderers are converted to MapLibre layers (circle/line/fill) and data-driven styles where applicable.

Endpoints:

```
# Base WMTS-only style
http://localhost:8089/maplibre-style

# Layer-specific style + GeoJSON
http://localhost:8089/maplibre-style?typename=layer_name
```

Customization example (client-side):

```javascript
map.setStyle('http://localhost:8089/maplibre-style?typename=roads');
```

## KASUGAI Canvas integration

The `/kasugai` endpoint (or the panel `Export` button for file output only, or the `kasugaiExport` bridge via Live Driver) exports the QGIS project to KASUGAI Canvas — a multi-engine map app (Cesium / OpenLayers / MapLibre / Leaflet).

```bash
curl "http://localhost:8089/kasugai?engine=openlayers"
# → {"ok":true,"url":"http://localhost:8510/?project=...&engine=openlayers","dir":"...","layers":N,"tiles":M,"engine":"openlayers"}
```

- Output: when the KASUGAI install location is registered in settings, projects are written to `<install>/QGIS_projects/<QGIS project name>/` (a dedicated folder kept separate from Canvas's own `projects/`); otherwise `<Documents>/kasugai_canvas_qgis` (`.kasc` + `DATA/`). Either way a running Canvas registers it as an external project
- GPKG/GeoJSON/GeoParquet/FlatGeobuf are referenced natively; other vectors are converted to GeoJSON (EPSG:4326)
- Each vector layer's QGIS style is bundled as `.qml` (compiled client-side — to Cesium rendering, and on the MapLibre/OpenLayers fronts too)
- WMS raster layers (non-`type=xyz`) are emitted as `wms:` lines (with `layers=`/`styles=`/`format=`); `wmts:` lines (RESTful templates, KVP GetTile) are also readable on the Canvas side
- The exported project opens on every engine via `?engine=cesium|maplibre|openlayers|leaflet` (`3dtiles:` lines render in 3D on Cesium/maplibre and top-down 2.5D via deck.gl on openlayers; leaflet lists them as unsupported rows on the info tab)
- Auto-registers and switches view on a running KASUGAI; output only when not running

See the "KASUGAI Canvas" section in `SPEC.md` for details.

## Office integration

### Excel

1. Generate a permalink in `geo_webview`
2. Insert hyperlink into an Excel cell
3. Click to jump the QGIS canvas to the location

### PowerPoint

1. Export a high-resolution PNG
2. Insert image into a slide
3. Attach a permalink to the image for interactive use during a presentation

## Development & customization

Repository layout (high level):

```
geo_webview/
├── plugin.py              # Main plugin
├── panel.py               # UI panel
├── server_manager.py      # HTTP server & routing
├── wms_service.py         # WMS implementation
├── wmts_service.py        # WMTS/XYZ implementation
├── wfs_service.py         # WFS implementation
├── maplibre/              # MapLibre style helpers (used by /maplibre-style)
├── kasugai_export.py      # KASUGAI Canvas integration
└── bridge.py              # AI/external control bridge
```

Read the technical details in `SPEC.md`.

Development steps:

1. Review `SPEC.md`
2. Inspect key modules
3. Test changes in QGIS
4. Iterate: change → test → commit

Translation support: English source strings with `i18n/<lang>.json` catalogs
(de, es, fr, hi, it, ja, pt, ru, zh). Edit the JSON directly —
untranslated strings fall back to English.

```bash
# list source strings not yet in the catalogs
python ../../scripts/i18n_tool.py check
```

## Security notes

⚠️ Important: This plugin is designed primarily for internal LAN use.

- Avoid publishing sensitive data publicly.
- For public exposure, add authentication and access control.
- With `External Control` enabled, external URLs can rewrite the QGIS view — use only on trusted networks.
- Configure firewalls appropriately and expose only minimal datasets.

## Roadmap & changelog

For the client integration strategy, see the [Integration architecture](#integration-architecture-development-direction) diagram.

- ✅ WMS/WMTS/WFS basics implemented
- ✅ Caching for performance
- ✅ MapLibre style conversion
- ✅ OL+Cesium 3D sync view & KASUGAI Canvas integration
- ⏳ Deeper Re:Earth Visualizer (geo_suite) integration (currently via generic GeoJSON/XYZ/QML)
- ❌ Full vector tile server (use external services)

See `CHANGELOG.md` for details.

## License

GNU General Public License v3 (GPLv3)

See `LICENSE`.

## Disclaimer

This software was developed and tested on a personal machine. Use at your own risk; the author is not liable for damages resulting from use.

<p align="center">
  <a href="https://giphy.com/explore/free-gif" target="_blank">
    <img src="https://github.com/yamamoto-ryuzo/QGIS_portable_3x/raw/master/imgs/giphy.gif" width="500" title="avvio QGIS">
  </a>
</p>
