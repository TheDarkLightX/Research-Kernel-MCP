"use client";
import { useEffect, useRef } from "react";
import { ArrowLeft, ArrowUpRight, Check, Circle, GitBranch, History, Play, Plus, Pencil, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { current, claimStatus, hasFailureHistory, hasNegativeEvidence, type Claim, type Receipt, type Workspace } from "@/lib/core/model";

export const kindNames = { hypothesis: "Hypothesis", literature: "Literature assertion", experiment: "Experimental result", formal: "Formal proof claim", bounded: "Bounded integer claim" };
const statusNames = { unverified: "Unverified", "bounded-checked": "Bounded check passed", counterexample: "Counterexample", "needs-review": "Needs review" };
export function Status({ value }: { value: keyof typeof statusNames }) {
  const Icon = value === "bounded-checked" ? Check : value === "unverified" ? Circle : TriangleAlert;
  return <span className={"badge status " + value}><Icon size={13} />{statusNames[value]}</span>;
}
function ReceiptCard({ receipt: r }: { receipt: Receipt }) {
  return <article className={"receipt " + (r.result.outcome === "counterexample" ? "failed" : "")}>
    <div className="receipt-title"><strong>{r.result.outcome === "passed" ? "Finite grid passed" : r.result.outcome === "counterexample" ? "Counterexample found" : "Check inconclusive"}</strong><span className="mono">{r.result.cases} / {r.result.totalCases} cases</span></div>
    <p>{r.result.scope}</p>
    {r.result.counterexample && <div className="counterexample"><span>Failing inputs</span><code>{Object.entries(r.result.counterexample.inputs).map(([k,v]) => `${k} = ${v}`).join(", ")}</code><span>Computed result</span><code>{r.result.counterexample.left} ≠ {r.result.counterexample.right}</code></div>}
    {r.result.error && <p role="status">{r.result.error}</p>}
    <details className="disclosure"><summary>Execution details & fingerprints</summary><dl className="fingerprints"><dt>Checker</dt><dd>{r.checker}</dd><dt>Environment</dt><dd>Exact BigInt arithmetic · 256-bit limit · 2,048-case limit</dd><dt>Created</dt><dd>{r.createdAt}</dd><dt>Claim revision</dt><dd>{r.claimRevision}</dd><dt>Recipe</dt><dd>{r.recipeHash}</dd><dt>Checker source</dt><dd>{r.checkerSourceHash}</dd><dt>Transcript</dt><dd>{r.transcriptHash}</dd><dt>Output digest</dt><dd>{r.result.outputsHash}</dd></dl></details>
    <p className="form-hint">Covers this recipe and finite grid. It does not establish a formal proof or an independent experimental replication.</p>
  </article>;
}
export function ClaimDetail({ workspace, claim, canWrite = false, owner = false, busy = false, historyFirst = false, onAction, onSelect, onBack }: {
  workspace: Workspace; claim: Claim; canWrite?: boolean; owner?: boolean; busy?: boolean; historyFirst?: boolean;
  onAction?: (action: "edit" | "evidence" | "publish" | "check") => void; onSelect: (id: string) => void; onBack: () => void;
}) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => { if (window.matchMedia("(max-width: 980px)").matches) headingRef.current?.focus({ preventScroll: true }); }, [claim.id]);
  const revision = current(claim);
  const receipts = workspace.receipts.filter(r => r.claimId === claim.id && r.claimRevision === revision.hash);
  const evidence = workspace.evidence.filter(e => e.claimId === claim.id && e.revisionHash === revision.hash);
  const status = claimStatus(workspace, claim);
  return <section className="claim-detail" aria-label="Claim inspector">
    <div className="inspector-heading"><Button className="back-to-list" variant="ghost" size="sm" onClick={() => { onBack(); requestAnimationFrame(() => document.getElementById("claim-" + claim.id)?.focus({ preventScroll: true })); }}><ArrowLeft />Back to claims</Button><span>{kindNames[revision.kind]}</span><span className="mono">r{revision.number}</span></div>
    <div className="inspector-title"><h2 ref={headingRef} tabIndex={-1}>{revision.title}</h2><div className="toolbar"><Status value={status} />{hasFailureHistory(workspace, claim) && <span className="history-note"><History size={13} />Failure history retained</span>}</div>
    {canWrite && <div className="detail-actions">{revision.recipe && <Button size="sm" disabled={busy || claim.needsReview} onClick={() => onAction?.("check")}><Play size={14} />Run check</Button>}<Button size="sm" variant="outline" disabled={busy} onClick={() => onAction?.("evidence")}><Plus size={14} />Add evidence</Button><Button size="sm" variant="ghost" disabled={busy} onClick={() => onAction?.("edit")}><Pencil size={14} />Revise</Button>{owner && <Button size="sm" variant="ghost" disabled={busy || claim.needsReview} onClick={() => onAction?.("publish")}><ArrowUpRight size={14} />Package</Button>}</div>}
    </div>
    <Tabs defaultValue={historyFirst ? "history" : "overview"} className="inspector-tabs">
      <TabsList variant="line" aria-label="Claim details"><TabsTrigger value="overview">Overview</TabsTrigger><TabsTrigger value="evidence">Evidence <span className="tab-count">{receipts.length + evidence.length}</span></TabsTrigger><TabsTrigger value="history">History <span className="tab-count">{claim.revisions.length}</span></TabsTrigger></TabsList>
      <TabsContent value="overview" className="inspector-content">
        {claim.needsReview && <div className="review-notice"><TriangleAlert size={18} /><div><strong>Review supporting claims</strong><p>A dependency changed or was challenged. Review it, then save a new revision before checking or publishing.</p></div></div>}
        {hasNegativeEvidence(workspace, claim) && <div className="review-notice"><TriangleAlert size={18} /><div><strong>Negative evidence attached</strong><p>Inspect the objection in Evidence. Its source assertion remains unverified.</p></div></div>}
        <section className="record-section"><h3>Statement</h3><p className="statement">{revision.statement}</p></section>
        <div className="scope-block"><section><h3>Scope & limits</h3><p>{revision.scope}</p></section><section><h3>Assumptions</h3><p>{revision.assumptions || "No assumptions recorded."}</p></section></div>
        <section className="record-section"><h3>Current verification</h3>{receipts.length ? <ReceiptCard receipt={receipts[receipts.length - 1]} /> : <p className="muted-copy">No checker receipt for this revision.{revision.kind !== "bounded" ? " This category requires external checking." : " Run a bounded check to record its result."}</p>}</section>
        {revision.dependencies.length > 0 && <section className="record-section"><h3>Supporting claims</h3>{revision.dependencies.map(id => { const dependency = workspace.claims.find(c => c.id === id); return <button className="dependency-link" key={id} onClick={() => onSelect(id)}><GitBranch size={16} /><span>{dependency ? current(dependency).title : id}</span>{dependency && <Status value={claimStatus(workspace, dependency)} />}<ArrowUpRight size={14} /></button>; })}</section>}
        {revision.recipe && <details className="disclosure recipe-disclosure"><summary>Exact replay recipe</summary><pre>{JSON.stringify(revision.recipe, null, 2)}</pre></details>}
        <details className="disclosure"><summary>Record provenance</summary><dl className="fingerprints"><dt>Record ID</dt><dd>{claim.id}</dd><dt>Revision hash</dt><dd>{revision.hash}</dd><dt>Created</dt><dd>{revision.createdAt}</dd>{claim.importedFrom && <><dt>Imported package</dt><dd>{claim.importedFrom}</dd></>}</dl></details>
      </TabsContent>
      <TabsContent value="evidence" className="inspector-content">
        <section className="record-section"><h3>Verification receipts <span>{receipts.length}</span></h3>{receipts.length ? receipts.slice().reverse().map(r => <ReceiptCard key={r.id} receipt={r} />) : <p className="muted-copy">No checker receipt for this revision.</p>}</section>
        <section className="record-section"><h3>Source evidence <span>{evidence.length}</span></h3>{evidence.length ? evidence.map(e => <article className="evidence" key={e.id}><span className="badge">{e.kind} · unverified</span><p>{e.summary}</p>{/^https?:/.test(e.uri) ? <a href={e.uri} target="_blank" rel="noreferrer" className="source-link">{e.uri}<ArrowUpRight size={13} /></a> : <code>{e.uri || "No source URI supplied"}</code>}{e.artifactHash && <details className="disclosure"><summary>Declared artifact fingerprint</summary><code>{e.artifactHash}</code></details>}</article>) : <p className="muted-copy">No source evidence attached yet.</p>}</section>
      </TabsContent>
      <TabsContent value="history" className="inspector-content">
        <p className="muted-copy history-intro">Earlier failures stay with the revision they tested. They do not determine the current revision’s status.</p>
        <div className="timeline">{claim.revisions.slice().reverse().map(r => <article className="timeline-item" key={r.hash}><div className="timeline-heading"><h3>Revision {r.number}</h3>{r.number === revision.number && <span className="badge">Current</span>}<time>{r.createdAt.slice(0, 10)}</time></div><p className="detail-text">{r.statement}</p><details className="disclosure"><summary>Scope, assumptions & recipe</summary><p>Scope: {r.scope}</p><p>Assumptions: {r.assumptions || "None recorded"}</p>{r.recipe && <pre>{JSON.stringify(r.recipe, null, 2)}</pre>}<code>{r.hash}</code></details>{workspace.receipts.filter(v => v.claimId === claim.id && v.claimRevision === r.hash).map(receipt => <ReceiptCard key={receipt.id} receipt={receipt} />)}{workspace.evidence.filter(e => e.claimId === claim.id && e.revisionHash === r.hash).map(e => <div className="evidence" key={e.id}><span className="badge">{e.kind} · unverified</span><p>{e.summary}</p><code>{e.uri}</code></div>)}</article>)}</div>
      </TabsContent>
    </Tabs>
  </section>;
}
