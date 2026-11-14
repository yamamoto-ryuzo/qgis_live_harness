# qgis_live_harness — リポジトリ横断ロジックシート

- 生成: 2026-11-14T07:12:38+09:00
- コンポーネント: geo_driver, geo_excel, geo_import, geo_launcher, geo_legend, geo_report, geo_search, geo_userfunc, geo_webview

## プラグイン間連携

```mermaid
flowchart LR
  subgraph SHARED["共有基盤"]
    DRV["geo_driver (LiveDriver/REST/MCP)"]
    TB["GeoSuite共有ツールバー"]
    REG["geo_userfunc 共有レジストリ"]
    ORG["layer_org 配置サービス"]
  end
  DRV -->|plugin_idルーティング/bridge_call| ALL["全プラグイン"]
  TB -->|ツールバー集約| ALL
  GEO_EXCEL["geo_excel"] -->|register_macro| REG
  GEO_IMPORT["geo_import"] -->|place_all| ORG
  AI["AI/エージェント"] -->|REST /api/cmd・MCP| DRV
```
