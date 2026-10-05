import { useState } from 'react'
import type { ULPIN } from '../types'
import { fmt } from '../utils/format'
import { Field } from './Layout'
import { StatusBadge } from './StatusBadge'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      className="btn btn--ghost btn--sm"
      onClick={() => {
        void navigator.clipboard?.writeText(text).then(() => {
          setCopied(true)
          window.setTimeout(() => setCopied(false), 1400)
        })
      }}
    >
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

/** The prototype identifier and the identity payload it is hashed from. */
export function UlpinPanel({ record, detailed }: { record: ULPIN; detailed?: boolean }) {
  return (
    <div className="ulpin">
      <div className="ulpin-head">
        <span className="eyebrow">Prototype 3D ULPIN</span>
        <StatusBadge tone="prototype" label={record.isOfficial ? 'Official' : 'Not official'} title={`is_official_ulpin: ${String(record.isOfficial)}`} />
      </div>
      <div className="ulpin-code-row">
        <code className="ulpin-code">{record.code}</code>
        <CopyButton text={record.code} />
      </div>
      <p className="note">{record.disclaimer}</p>
      <dl className="fields">
        <Field label="Property unit" mono>{record.unitId}</Field>
        <Field label="Building" mono>{record.buildingId}</Field>
        <Field label="Storey">{record.storeyNames.join(', ')}</Field>
        <Field label="Geometry version" mono>{record.geometryVersion}</Field>
        <Field label="Vertical extent">{fmt(record.verticalExtentM[0])} → {fmt(record.verticalExtentM[1])} m</Field>
        <Field label="Parcel">{record.parcelId ?? <StatusBadge raw={record.cadastralStatus} />}</Field>
        <Field label="Validation"><StatusBadge raw={record.validationStatus} /></Field>
        {detailed && (
          <>
            <Field label="Scheme" mono>{record.scheme}</Field>
            <Field label="Dataset">{record.dataset}</Field>
            <Field label="Identifier class" mono>{record.identifierClass}</Field>
            <Field label="Issuer" stack>{record.issuer}</Field>
            <Field label="Derivation" stack><span className="mono">{record.derivationMethod}</span></Field>
            <Field label="Legal status"><StatusBadge raw={record.legalStatus} /></Field>
            <Field label="Ownership"><StatusBadge raw={record.ownershipStatus} /></Field>
            <Field label="Unit status"><StatusBadge raw={record.unitStatus} /></Field>
            <Field label="Unit confidence">{record.unitConfidence.toFixed(2)}</Field>
            <Field label="Geometry confidence">{record.geometryConfidence.toFixed(2)}</Field>
          </>
        )}
      </dl>
      <details className="disclosure" open={detailed}>
        <summary>Source IDs · {record.sourceIds.length} IfcSpace GlobalIds</summary>
        <ul className="id-list mono">
          {record.sourceIds.map((id) => <li key={id}>{id}</li>)}
        </ul>
      </details>
    </div>
  )
}
