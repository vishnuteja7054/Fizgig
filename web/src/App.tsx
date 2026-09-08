import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { importDataset, loadWorkspaceState, readCaption, removeDatasetItem, resizeOnly, scanDataset, updateWorkspaceState, writeCaption, writeTrainingDatasetConfig } from "./api";
import type { ImagePrepResult, TrainingConfigResult } from "./api";
import type { DatasetItem, SectionKey } from "./types";

const sections: Array<{ key: SectionKey; label: string; icon: string; group?: string }> = [
  { key: "start", label: "Start", icon: "⌂" },
  { key: "prep", label: "Image Prep", icon: "✦" },
  { key: "captions", label: "Captions", icon: "Aa" },
  { key: "samples", label: "Samples", icon: "◈" },
  { key: "training", label: "Training", icon: "↗" },
  { key: "profiler", label: "Profiler", icon: "◎", group: "Workbench" },
  { key: "repair", label: "Repair Studio", icon: "⌘", group: "Workbench" },
  { key: "explorer", label: "LoRA Explorer", icon: "◇", group: "Workbench" },
  { key: "royale", label: "LoRA Royale", icon: "♢", group: "Workbench" },
  { key: "extract", label: "Extract", icon: "⇩", group: "Workbench" },
  { key: "metadata", label: "Metadata", icon: "≡", group: "Tools" },
  { key: "preferences", label: "Preferences", icon: "⚙", group: "Tools" },
];

function App() {
  const [active, setActive] = useState<SectionKey>("start");
  const [folder, setFolder] = useState("dataset");
  const [items, setItems] = useState<DatasetItem[]>([]);
  const [selected, setSelected] = useState<DatasetItem | null>(null);
  const [caption, setCaption] = useState("");
  const [prepTargetMegapixels, setPrepTargetMegapixels] = useState("1.0");
  const [prepReplaceOriginals, setPrepReplaceOriginals] = useState(false);
  const [prepResult, setPrepResult] = useState<ImagePrepResult | null>(null);
  const [trainingConfigName, setTrainingConfigName] = useState("Fizgig_train");
  const [trainingMegapixels, setTrainingMegapixels] = useState("0.25");
  const [trainingBatchSize, setTrainingBatchSize] = useState("1");
  const [trainingEnableBucket, setTrainingEnableBucket] = useState(true);
  const [trainingNoUpscale, setTrainingNoUpscale] = useState(true);
  const [trainingConfigResult, setTrainingConfigResult] = useState<TrainingConfigResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("Ready");
  const [error, setError] = useState("");

  const captionCount = useMemo(() => items.filter((item) => item.has_caption).length, [items]);
  const missingCount = items.length - captionCount;

  async function scan() {
    setLoading(true);
    setError("");
    try {
      void updateWorkspaceState({ dataset_folder: folder.trim() }).catch(() => undefined);
      const result = await scanDataset(folder.trim());
      setItems(result.items);
      setSelected(null);
      setCaption("");
      setMessage(`Scanned ${result.items.length} training item${result.items.length === 1 ? "" : "s"}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to scan dataset");
      setMessage("Scan failed");
    } finally {
      setLoading(false);
    }
  }

  async function importSelectedFolder(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? []);
    event.target.value = "";
    const importableFiles = selectedFiles.filter((file) =>
      /\.(jpg|jpeg|png|gif|bmp|webp|tiff?|mp4|wav|mp3|flac|m4a|txt)$/i.test(file.name),
    );
    if (importableFiles.length === 0) {
      setError("The selected folder contains no supported media or caption files.");
      return;
    }
    const destination = folder.trim() || "dataset";
    setLoading(true);
    setError("");
    try {
      void updateWorkspaceState({ dataset_folder: destination }).catch(() => undefined);
      const result = await importDataset(destination, importableFiles);
      const scanResult = await scanDataset(destination);
      setItems(scanResult.items);
      setSelected(null);
      setCaption("");
      const skippedMessage = result.skipped.length ? `; ${result.skipped.length} already existed/skipped` : "";
      setMessage(`Imported ${result.imported.length} file${result.imported.length === 1 ? "" : "s"} into ${destination}${skippedMessage}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to import folder");
      setMessage("Import failed");
    } finally {
      setLoading(false);
    }
  }

  async function selectItem(item: DatasetItem) {
    setSelected(item);
    setError("");
    try {
      const result = await readCaption(item.relative_path);
      setCaption(result.text);
    } catch (cause) {
      setCaption("");
      setError(cause instanceof Error ? cause.message : "Unable to read caption");
    }
  }

  async function prepareResizeOnly() {
    const target = Number(prepTargetMegapixels);
    if (!folder.trim() || !Number.isFinite(target) || target <= 0) {
      setError("Choose a dataset folder and a valid target size.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      void updateWorkspaceState({
        dataset_folder: folder.trim(),
        prep_megapixels: prepTargetMegapixels,
        prep_replace_originals: prepReplaceOriginals,
      }).catch(() => undefined);
      const result = await resizeOnly(folder.trim(), target, prepReplaceOriginals);
      setPrepResult(result);
      const scanResult = await scanDataset(folder.trim());
      setItems(scanResult.items);
      setSelected(null);
      setCaption("");
      setMessage(`Prepared ${result.converted} image${result.converted === 1 ? "" : "s"}; ${result.skipped} skipped, ${result.errors} errors`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to prepare images");
      setMessage("Image preparation failed");
    } finally {
      setLoading(false);
    }
  }

  async function saveTrainingDatasetConfig() {
    const target = Number(trainingMegapixels);
    const batch = Number(trainingBatchSize);
    if (!folder.trim() || !Number.isFinite(target) || target <= 0 || !Number.isInteger(batch) || batch < 1) {
      setError("Choose a dataset folder and valid training values.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await writeTrainingDatasetConfig({
        name: trainingConfigName.trim() || "Fizgig_train",
        folder: folder.trim(),
        target_megapixels: target,
        batch_size: batch,
        caption_extension: ".txt",
        enable_bucket: trainingEnableBucket,
        bucket_no_upscale: trainingNoUpscale,
        cache_root: "cache",
      });
      setTrainingConfigResult(result);
      void updateWorkspaceState({
        dataset_folder: folder.trim(),
        training_config_name: trainingConfigName.trim() || "Fizgig_train",
        dataset_megapixels: trainingMegapixels,
        dataset_batch_size: String(batch),
        dataset_enable_bucket: trainingEnableBucket,
        dataset_no_upscale: trainingNoUpscale,
      }).catch(() => undefined);
      setMessage(`Saved ${result.config_relative_path}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save training config");
      setMessage("Training config failed");
    } finally {
      setLoading(false);
    }
  }

  async function saveSelectedCaption() {
    if (!selected) return;
    setError("");
    try {
      await writeCaption(selected.relative_path, caption);
      setItems((current) => current.map((item) =>
        item.relative_path === selected.relative_path ? { ...item, has_caption: true } : item,
      ));
      setMessage(`Saved ${selected.caption_relative_path}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save caption");
    }
  }

  async function removeSelected(item: DatasetItem) {
    setError("");
    try {
      await removeDatasetItem(item.relative_path);
      setItems((current) => current.filter((candidate) => candidate.relative_path !== item.relative_path));
      if (selected?.relative_path === item.relative_path) {
        setSelected(null);
        setCaption("");
      }
      setMessage(`Moved ${item.relative_path} to removed/`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to remove item");
    }
  }

  useEffect(() => {
    void loadWorkspaceState()
      .then((result) => {
        const savedFolder = result.values.dataset_folder;
        if (typeof savedFolder === "string" && savedFolder.trim()) setFolder(savedFolder);
        const savedMegapixels = result.values.prep_megapixels;
        if (typeof savedMegapixels === "string") setPrepTargetMegapixels(savedMegapixels);
        if (typeof result.values.prep_replace_originals === "boolean") {
          setPrepReplaceOriginals(result.values.prep_replace_originals);
        }
      })
      .catch(() => {
        // The UI remains usable with defaults while an older API is restarting.
      });
  }, []);

  useEffect(() => {
    if (active === "captions" && items.length === 0) void scan();
    // The scan is intentionally tied to navigation only; it does not run on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const grouped = [
    { label: "Workspace", items: sections.filter((section) => !section.group) },
    { label: "Workbench", items: sections.filter((section) => section.group === "Workbench") },
    { label: "Tools", items: sections.filter((section) => section.group === "Tools") },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">F</div>
          <div><strong>Fizgig</strong><span>LoRA workbench</span></div>
        </div>
        <div className="sidebar-scroll">
          {grouped.map((group) => (
            <div className="nav-group" key={group.label}>
              <div className="nav-heading">{group.label}</div>
              {group.items.map((section) => (
                <button
                  className={`nav-item ${active === section.key ? "active" : ""}`}
                  key={section.key}
                  onClick={() => setActive(section.key)}
                >
                  <span className="nav-icon">{section.icon}</span>
                  <span>{section.label}</span>
                  {!["start", "captions", "training"].includes(section.key) && <span className="soon-dot" />}
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="sidebar-footer">
          <span className="status-dot" />
          <span>Browser migration</span>
          <span className="version">0.1</span>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div>
            <div className="eyebrow">WORKBENCH / {active.toUpperCase()}</div>
            <h1>{sections.find((section) => section.key === active)?.label}</h1>
          </div>
          <div className="topbar-actions">
            <div className="connection"><span className="status-dot" /> API connected</div>
            <button className="icon-button" aria-label="Help">?</button>
            <div className="avatar">V</div>
          </div>
        </header>

        <div className="content">
          {error && <div className="alert error"><span>!</span>{error}</div>}
          <div className="status-line"><span>{message}</span>{loading && <span className="spinner" />}</div>

          {active === "start" && (
            <StartPage
              folder={folder}
              setFolder={setFolder}
              items={items}
              captionCount={captionCount}
              missingCount={missingCount}
              loading={loading}
              onScan={scan}
              onImport={importSelectedFolder}
              onOpenCaptions={() => setActive("captions")}
              onSelect={selectItem}
              onRemove={removeSelected}
            />
          )}
          {active === "captions" && (
            <CaptionsPage
              folder={folder}
              items={items}
              selected={selected}
              caption={caption}
              setCaption={setCaption}
              onSelect={selectItem}
              onSave={saveSelectedCaption}
              onScan={scan}
              onRemove={removeSelected}
            />
          )}
          {active === "prep" && (
            <ImagePrepPage
              folder={folder}
              targetMegapixels={prepTargetMegapixels}
              setTargetMegapixels={setPrepTargetMegapixels}
              replaceOriginals={prepReplaceOriginals}
              setReplaceOriginals={setPrepReplaceOriginals}
              loading={loading}
              result={prepResult}
              onRun={prepareResizeOnly}
            />
          )}
          {active === "training" && (
            <TrainingPage
              folder={folder}
              configName={trainingConfigName}
              setConfigName={setTrainingConfigName}
              megapixels={trainingMegapixels}
              setMegapixels={setTrainingMegapixels}
              batchSize={trainingBatchSize}
              setBatchSize={setTrainingBatchSize}
              enableBucket={trainingEnableBucket}
              setEnableBucket={setTrainingEnableBucket}
              noUpscale={trainingNoUpscale}
              setNoUpscale={setTrainingNoUpscale}
              loading={loading}
              result={trainingConfigResult}
              onSave={saveTrainingDatasetConfig}
            />
          )}
          {active !== "start" && active !== "captions" && active !== "prep" && active !== "training" && <ComingSoonPage section={active} />}
        </div>
      </main>
    </div>
  );
}

function StartPage(props: {
  folder: string;
  setFolder: (value: string) => void;
  items: DatasetItem[];
  captionCount: number;
  missingCount: number;
  loading: boolean;
  onScan: () => void;
  onImport: (event: ChangeEvent<HTMLInputElement>) => void;
  onOpenCaptions: () => void;
  onSelect: (item: DatasetItem) => void;
  onRemove: (item: DatasetItem) => void;
}) {
  return (
    <>
      <section className="hero-card">
        <div className="hero-copy">
          <div className="pill accent">FIRST VERTICAL SLICE</div>
          <h2>Turn a folder into a<br /><span>workable dataset.</span></h2>
          <p>Scan your workspace, review the media Fizgig will train on, and keep captions in sync before a run begins.</p>
        </div>
        <div className="hero-orbit"><div className="orbit-ring ring-one" /><div className="orbit-ring ring-two" /><div className="orbit-core">F</div></div>
      </section>

      <section className="card workspace-card">
        <div className="section-heading"><div><div className="section-kicker">DATASET WORKSPACE</div><h3>Choose a training folder</h3></div><span className="pill">SAFE PATHS</span></div>
        <div className="field-row">
          <label className="path-field"><span className="field-icon">⌁</span><input value={props.folder} onChange={(event) => props.setFolder(event.target.value)} onKeyDown={(event) => event.key === "Enter" && props.onScan()} placeholder="dataset/my-subject" /><span className="field-suffix">workspace-relative</span></label>
          <button className="button primary" disabled={props.loading || !props.folder.trim()} onClick={props.onScan}>{props.loading ? "Scanning…" : "Scan folder"}<span>→</span></button>
        </div>
        <div className="import-row">
          <label className="button ghost folder-picker-button">
            {props.loading ? "Importing…" : "Choose local folder"}<span>＋</span>
            <input
              className="folder-picker-input"
              type="file"
              multiple
              accept=".jpg,.jpeg,.png,.gif,.bmp,.webp,.tif,.tiff,.mp4,.wav,.mp3,.flac,.m4a,.txt"
              onChange={props.onImport}
              {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
            />
          </label>
          <div className="helper-text">Choose a folder from this PC; supported files are copied into the workspace path above. Existing files are never overwritten.</div>
        </div>
        <div className="helper-text">Or type a path already inside the configured Fizgig workspace. Subfolders such as <code>removed/</code> are intentionally not scanned.</div>
      </section>

      <div className="metric-grid">
        <Metric label="Training items" value={String(props.items.length).padStart(2, "0")} tone="blue" />
        <Metric label="Captioned" value={String(props.captionCount).padStart(2, "0")} tone="green" />
        <Metric label="Needs captions" value={String(props.missingCount).padStart(2, "0")} tone="amber" />
      </div>

      <DatasetTable items={props.items} onOpenCaptions={props.onOpenCaptions} onSelect={props.onSelect} onRemove={props.onRemove} />
    </>
  );
}

function CaptionsPage(props: {
  folder: string;
  items: DatasetItem[];
  selected: DatasetItem | null;
  caption: string;
  setCaption: (value: string) => void;
  onSelect: (item: DatasetItem) => void;
  onSave: () => void;
  onScan: () => void;
  onRemove: (item: DatasetItem) => void;
}) {
  return (
    <div className="caption-layout">
      <section className="card caption-list-card">
        <div className="section-heading"><div><div className="section-kicker">CAPTION QUEUE</div><h3>{props.items.length} media items</h3></div><button className="button ghost small" onClick={props.onScan}>Refresh</button></div>
        <div className="caption-list">
          {props.items.length === 0 && <EmptyState text="Scan a dataset from Start to begin." />}
          {props.items.map((item) => <DatasetListRow item={item} selected={props.selected?.relative_path === item.relative_path} onSelect={props.onSelect} onRemove={props.onRemove} key={item.relative_path} />)}
        </div>
      </section>
      <section className="card editor-card">
        {props.selected ? <>
          <div className="section-heading"><div><div className="section-kicker">EDITING CAPTION</div><h3>{props.selected.relative_path.split("/").pop()}</h3></div><span className={`type-badge ${props.selected.kind}`}>{props.selected.kind}</span></div>
          <div className="editor-preview"><div className="preview-glyph">{props.selected.kind === "audio" ? "◖" : props.selected.kind === "video" ? "▶" : "✦"}</div><span>{props.selected.relative_path}</span></div>
          <label className="editor-label">Caption text<textarea value={props.caption} onChange={(event) => props.setCaption(event.target.value)} placeholder="Describe the subject, view, setting, and details…" /></label>
          <div className="editor-actions"><span className="helper-text">Saved as {props.selected.caption_relative_path}</span><button className="button primary" onClick={props.onSave}>Save caption <span>✓</span></button></div>
        </> : <EmptyState text="Select an item to edit its caption." large />}
      </section>
    </div>
  );
}

function ImagePrepPage(props: {
  folder: string;
  targetMegapixels: string;
  setTargetMegapixels: (value: string) => void;
  replaceOriginals: boolean;
  setReplaceOriginals: (value: boolean) => void;
  loading: boolean;
  result: ImagePrepResult | null;
  onRun: () => void;
}) {
  return <>
    <section className="card prep-banner">
      <div><div className="section-kicker">IMAGE PREP / RESIZE ONLY</div><h2>Prepare images for training</h2><p>Convert the selected workspace folder to PNG while preserving aspect ratio and matching Fizgig’s 16-pixel training grid.</p></div>
      <span className="pill accent">NO MODEL REQUIRED</span>
    </section>
    <section className="card prep-options">
      <div className="section-heading"><div><div className="section-kicker">CURRENT FOLDER</div><h3>{props.folder || "No folder selected"}</h3></div><span className="pill">SAFE OUTPUTS</span></div>
      <div className="prep-control-grid">
        <label className="prep-control"><span>Target megapixels</span><select value={props.targetMegapixels} onChange={(event) => props.setTargetMegapixels(event.target.value)}><option value="0.25">0.25 MP</option><option value="0.5">0.5 MP</option><option value="0.75">0.75 MP</option><option value="1.0">1.0 MP</option><option value="1.5">1.5 MP</option><option value="2.0">2.0 MP</option><option value="2.4">2.4 MP</option><option value="3.0">3.0 MP</option><option value="4.2">4.2 MP</option></select></label>
        <label className="prep-check"><input type="checkbox" checked={props.replaceOriginals} onChange={(event) => props.setReplaceOriginals(event.target.checked)} /><span><strong>Replace originals</strong><small>Destructive: original files will not be moved to <code>originals/</code>.</small></span></label>
      </div>
      <div className="prep-actions"><button className="button primary" disabled={props.loading || !props.folder} onClick={props.onRun}>{props.loading ? "Preparing…" : "Prepare images"}<span>→</span></button><span className="helper-text">Resize only is available now. Face crop modes will use a separate worker once face-tool dependencies are exposed.</span></div>
    </section>
    <section className="card table-card">
      <div className="section-heading"><div><div className="section-kicker">PREPARATION REPORT</div><h3>{props.result ? `${props.result.converted} converted · ${props.result.skipped} skipped · ${props.result.errors} errors` : "No preparation run yet"}</h3></div></div>
      {!props.result ? <EmptyState text="Choose a folder on Start, then run Resize only here." /> : <div className="table-wrap"><table><thead><tr><th>Source</th><th>Status</th><th>Output</th><th>Size</th></tr></thead><tbody>{props.result.files.map((item) => <tr key={item.source_relative_path}><td>{item.source_relative_path}</td><td><span className={`caption-state ${item.status === "error" ? "missing" : "ready"}`}>{item.status}</span></td><td>{item.output_relative_path ?? item.detail}</td><td>{item.output_size ? `${item.output_size[0]} × ${item.output_size[1]}` : "—"}</td></tr>)}</tbody></table></div>}
    </section>
  </>;
}

function TrainingPage(props: {
  folder: string;
  configName: string;
  setConfigName: (value: string) => void;
  megapixels: string;
  setMegapixels: (value: string) => void;
  batchSize: string;
  setBatchSize: (value: string) => void;
  enableBucket: boolean;
  setEnableBucket: (value: boolean) => void;
  noUpscale: boolean;
  setNoUpscale: (value: boolean) => void;
  loading: boolean;
  result: TrainingConfigResult | null;
  onSave: () => void;
}) {
  return <>
    <section className="card prep-banner training-banner">
      <div><div className="section-kicker">TRAINING / DATASET CONTRACT</div><h2>Build a compatible training config</h2><p>These values write the same TOML dataset contract used by Fizgig’s existing training scripts. Actual model jobs will attach to this config through the durable job runner.</p></div>
      <span className="pill accent">CONFIG ONLY</span>
    </section>
    <section className="card prep-options">
      <div className="section-heading"><div><div className="section-kicker">DATASET CONFIGURATION</div><h3>{props.folder || "No folder selected"}</h3></div><span className="pill">FIZGIG_TRAIN.TOML</span></div>
      <div className="training-form-grid">
        <label className="prep-control"><span>Config name</span><input value={props.configName} onChange={(event) => props.setConfigName(event.target.value)} placeholder="Fizgig_train" /></label>
        <label className="prep-control"><span>Target megapixels</span><select value={props.megapixels} onChange={(event) => props.setMegapixels(event.target.value)}><option value="0.25">0.25 MP</option><option value="0.5">0.5 MP</option><option value="0.75">0.75 MP</option><option value="1.0">1.0 MP</option><option value="1.5">1.5 MP</option><option value="2.0">2.0 MP</option></select></label>
        <label className="prep-control"><span>Batch size</span><input type="number" min="1" max="1024" value={props.batchSize} onChange={(event) => props.setBatchSize(event.target.value)} /></label>
      </div>
      <div className="training-checks"><label><input type="checkbox" checked={props.enableBucket} onChange={(event) => props.setEnableBucket(event.target.checked)} /> Enable resolution buckets</label><label><input type="checkbox" checked={props.noUpscale} onChange={(event) => props.setNoUpscale(event.target.checked)} /> Never upscale images</label></div>
      <div className="prep-actions"><button className="button primary" disabled={props.loading || !props.folder} onClick={props.onSave}>{props.loading ? "Saving…" : "Save dataset config"}<span>✓</span></button><span className="helper-text">Dataset folder is selected on Start. Model paths, presets, and job execution will be connected in the next training slices.</span></div>
    </section>
    <section className="card config-preview"><div className="section-heading"><div><div className="section-kicker">GENERATED ARTIFACT</div><h3>{props.result?.config_relative_path ?? "No config saved yet"}</h3></div></div>{props.result ? <pre>{props.result.content}</pre> : <EmptyState text="Save the configuration to generate a compatible TOML file." />}</section>
  </>;
}

function DatasetTable(props: { items: DatasetItem[]; onOpenCaptions: () => void; onSelect: (item: DatasetItem) => void; onRemove: (item: DatasetItem) => void }) {
  return <section className="card table-card">
    <div className="section-heading"><div><div className="section-kicker">MEDIA INVENTORY</div><h3>Dataset contents</h3></div>{props.items.length > 0 && <button className="button ghost small" onClick={props.onOpenCaptions}>Open captions <span>→</span></button>}</div>
    {props.items.length === 0 ? <EmptyState text="Scan a folder to see its training items." /> : <div className="table-wrap"><table><thead><tr><th>Item</th><th>Type</th><th>Caption</th><th /></tr></thead><tbody>{props.items.map((item) => <tr key={item.relative_path}><td><button className="file-link" onClick={() => props.onSelect(item)}><span className="file-glyph">{item.kind === "audio" ? "♪" : item.kind === "video" ? "▣" : "▧"}</span>{item.relative_path}</button></td><td><span className={`type-badge ${item.kind}`}>{item.kind}</span></td><td>{item.has_caption ? <span className="caption-state ready">Ready</span> : <span className="caption-state missing">Missing</span>}</td><td><button className="row-action" onClick={() => props.onRemove(item)}>Move to removed</button></td></tr>)}</tbody></table></div>}
  </section>;
}

function DatasetListRow(props: { item: DatasetItem; selected: boolean; onSelect: (item: DatasetItem) => void; onRemove: (item: DatasetItem) => void }) {
  return <div className={`caption-row ${props.selected ? "selected" : ""}`}><button className="caption-row-main" onClick={() => props.onSelect(props.item)}><span className={`media-icon ${props.item.kind}`}>{props.item.kind === "audio" ? "♪" : props.item.kind === "video" ? "▶" : "✦"}</span><span><strong>{props.item.relative_path.split("/").pop()}</strong><small>{props.item.has_caption ? "Caption ready" : "Needs caption"}</small></span></button><button className="mini-action" title="Move to removed" onClick={() => props.onRemove(props.item)}>···</button></div>;
}

function Metric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return <div className="metric card"><span className={`metric-mark ${tone}`} /><div><span>{label}</span><strong>{value}</strong></div></div>;
}

function ComingSoonPage({ section }: { section: SectionKey }) {
  const labels: Record<SectionKey, string> = { start: "Start", prep: "Image Prep", captions: "Captions", samples: "Samples", training: "Training", profiler: "Profiler", repair: "Repair Studio", explorer: "LoRA Explorer", royale: "LoRA Royale", extract: "Extract", metadata: "Metadata", preferences: "Preferences" };
  return <section className="card rollout-card"><div className="rollout-icon">✦</div><div className="pill accent">CONTROLLED ROLLOUT</div><h2>{labels[section]} is next</h2><p>The browser shell is in place. This surface will be wired to the existing Fizgig engine behind a durable API and job contract before controls are enabled.</p><div className="rollout-rule"><span>Current milestone</span><strong>Start + Captions vertical slice</strong></div></section>;
}

function EmptyState({ text, large = false }: { text: string; large?: boolean }) {
  return <div className={`empty-state ${large ? "large" : ""}`}><div className="empty-icon">◌</div><span>{text}</span></div>;
}

export default App;
