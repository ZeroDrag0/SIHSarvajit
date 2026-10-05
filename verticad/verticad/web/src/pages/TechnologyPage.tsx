import { Page, Panel } from '../components/Layout'
import { StatusBadge } from '../components/StatusBadge'
import { useDataset } from '../services/datasetContext'

export function TechnologyPage() {
 const { provenance, metrics, cadastral } = useDataset()
 const methods = provenance.status === 'ready' ? provenance.data.methods : []
 return <Page eyebrow="Technology" title="A 3D cadastral pipeline, not a black box." lede="VERTICAD turns spatial source data into structured property geometry, validates the result, and derives a prototype 3D property identity. Each stage records what was actually available.">
   <div className="tech-flow">{['Spatial data','Extraction','Property mapping','Validation','3D Property ID','Cadastral model'].map((x,i)=><div key={x}><span>{String(i+1).padStart(2,'0')}</span><strong>{x}</strong>{i<5&&<b>→</b>}</div>)}</div>
   <div className="grid-2">
    <Panel title="Implemented in this demonstrator">
      <ul className="tech-list">{['IFC/BIM ingestion and spatial extraction','Floor and room classification','Property-unit inference from spatial evidence','3D geometry generation and provenance','Topology / geometry validation','Deterministic prototype 3D ULPIN generation','Interoperable 3D cadastral model'].map(x=><li key={x}><i>✓</i>{x}</li>)}</ul>
    </Panel>
    <Panel title="Designed for additional sources">
      <ul className="tech-list">{['LiDAR / 3D survey corroboration','GIS land parcels and property boundaries','GNSS / CORS survey reference','Ground and surface elevation models','Underground utility volumes','AI-assisted building and floor extraction'].map(x=><li key={x}><i>+</i>{x}</li>)}</ul>
      <p className="note">A capability is not presented as live simply because the architecture supports it. Source status is exposed on the Data page.</p>
    </Panel>
   </div>
   <Panel title="Processing stages">
    <div className="tech-stage-list">{methods.map((m,i)=><div key={m.stage}><span>{String(i+1).padStart(2,'0')}</span><div><strong>{m.stage.replaceAll('_',' ')}</strong><small>{m.methodType ?? 'Method recorded by pipeline'}</small></div><StatusBadge raw={m.modelStatus ?? m.methodType ?? 'derived'} /></div>)}</div>
   </Panel>
   <Panel title="Interoperability principles">
    <div className="principles"><div><strong>Traceable</strong><span>Every derived result keeps its source and method.</span></div><div><strong>3D-native</strong><span>Property is represented as a spatial volume, not only a coordinate.</span></div><div><strong>Open to authority data</strong><span>Parcels, survey control and underground records can be attached when authorized.</span></div><div><strong>Prototype-safe</strong><span>The demonstrator never labels a derived identifier as an official government ULPIN.</span></div></div>
   </Panel>
   <p className="note">Current model: {metrics.buildings} building · {metrics.storeys} floor levels · {metrics.propertyUnits} property units · cadastral model {cadastral.modelVersion}.</p>
 </Page>
}
