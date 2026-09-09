import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, ReactNode } from "react";
import { artifactDownloadUrl, cancelJob, clearSampleOverride, deletePreset, getJob, importDataset, inspectMetadata, listJobs, listPresets, loadLoraExplorer, loadLoraRoyale, loadPreset, loadRepairDefaultState, loadWorkspaceState, previewExtract, previewProfile, previewRepairBake, previewRepairRender, previewTrainingCommand, readCaption, removeDatasetItem, savePreset, scanDataset, startExtract, startExplorerRender, startProfile, startRepairBake, startRepairRender, startResizeOnlyJob, startRoyaleRender, startTrainingJob, updateWorkspaceState, writeCaption, writeSampleOverride, writeSamplePrompts, writeTrainingDatasetConfig } from "./api";
import type { ImagePrepResult, LoraCatalogItem, MetadataInspection, TrainingCommandPreview, TrainingConfigResult, WorkbenchPreview } from "./api";
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
  { key: "jobs", label: "Jobs", icon: "◷", group: "Tools" },
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
  const [trainingArchitecture, setTrainingArchitecture] = useState("Flux 2 Klein Base 9B");
  const [trainingDit, setTrainingDit] = useState("");
  const [trainingVae, setTrainingVae] = useState("");
  const [trainingTextEncoder, setTrainingTextEncoder] = useState("");
  const [trainingOutputDir, setTrainingOutputDir] = useState("output_loras");
  const [trainingOutputName, setTrainingOutputName] = useState("fizgig_lora");
  const [trainingEpochs, setTrainingEpochs] = useState("10");
  const [trainingRank, setTrainingRank] = useState("16");
  const [trainingLearningRate, setTrainingLearningRate] = useState("0.0001");
  const [trainingBlocksSwap, setTrainingBlocksSwap] = useState("0");
  const [trainingCommand, setTrainingCommand] = useState<TrainingCommandPreview | null>(null);
  const [sampleText, setSampleText] = useState("A high quality photo");
  const [sampleName, setSampleName] = useState("prompts.txt");
  const [samplePromptFile, setSamplePromptFile] = useState("");
  const [sampleEveryEpochs, setSampleEveryEpochs] = useState("1");
  const [sampleAtFirst, setSampleAtFirst] = useState(true);
  const [sampleWidth, setSampleWidth] = useState("768");
  const [sampleHeight, setSampleHeight] = useState("768");
  const [sampleSteps, setSampleSteps] = useState("40");
  const [sampleSeed, setSampleSeed] = useState("1234");
  const [sampleOverridePrompt, setSampleOverridePrompt] = useState("");
  const [profilerLora, setProfilerLora] = useState("");
  const [profilerOutput, setProfilerOutput] = useState("out/profile.html");
  const [profilerPreview, setProfilerPreview] = useState<WorkbenchPreview | null>(null);
  const [extractSource, setExtractSource] = useState("");
  const [extractOutput, setExtractOutput] = useState("output_loras/extracted.safetensors");
  const [extractSamples, setExtractSamples] = useState("0");
  const [extractRank, setExtractRank] = useState("2");
  const [extractPreview, setExtractPreview] = useState<WorkbenchPreview | null>(null);
  const [repairFamily, setRepairFamily] = useState("klein");
  const [repairPrimary, setRepairPrimary] = useState("");
  const [repairDonor, setRepairDonor] = useState("");
  const [repairOutput, setRepairOutput] = useState("output_loras/repaired.safetensors");
  const [repairPreviewOutput, setRepairPreviewOutput] = useState("out/repair_preview.png");
  const [repairStateJson, setRepairStateJson] = useState("{}\n");
  const [repairPreview, setRepairPreview] = useState<{ operation: string; primary: string; donor: string; output: string; execution_ready: boolean } | null>(null);
  const [repairRenderPreview, setRepairRenderPreview] = useState<{ operation: string; family: string; output: string; execution_ready: boolean } | null>(null);
  const [metadataPath, setMetadataPath] = useState("");
  const [metadataResult, setMetadataResult] = useState<MetadataInspection | null>(null);
  const [catalogFolder, setCatalogFolder] = useState("output_loras");
  const [catalogFamily, setCatalogFamily] = useState("klein");
  const [catalogPrimary, setCatalogPrimary] = useState("");
  const [catalogPrompt, setCatalogPrompt] = useState("A high quality photo");
  const [catalogOutput, setCatalogOutput] = useState("out/workbench");
  const [explorerItems, setExplorerItems] = useState<LoraCatalogItem[]>([]);
  const [royaleItems, setRoyaleItems] = useState<LoraCatalogItem[]>([]);
  const [presetNames, setPresetNames] = useState<string[]>([]);
  const [selectedPreset, setSelectedPreset] = useState("");
  const [presetName, setPresetName] = useState("");
  const [presetJson, setPresetJson] = useState("{}\n");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("Ready");
  const [error, setError] = useState("");
  const [jobs, setJobs] = useState<import("./api").JobRecord[]>([]);

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
      const started = await startResizeOnlyJob(folder.trim(), target, prepReplaceOriginals);
      let job = started;
      while (["queued", "starting", "running", "cancel_requested"].includes(job.status)) {
        setMessage(`${job.message} · ${Math.round(job.progress)}%`);
        await new Promise((resolve) => window.setTimeout(resolve, 350));
        job = await getJob(started.id);
      }
      if (job.status !== "completed") throw new Error(job.error || `Image preparation ${job.status}`);
      const result = job.result as ImagePrepResult;
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

  function launchValues() {
    const config = trainingConfigResult?.config_relative_path;
    if (!config) throw new Error("Save the dataset config before preparing a training launch.");
    const epochs = Number(trainingEpochs);
    const rank = Number(trainingRank);
    const learningRate = Number(trainingLearningRate);
    if (!trainingDit.trim() || !Number.isInteger(epochs) || epochs < 1 || !Number.isInteger(rank) || rank < 1 || !Number.isFinite(learningRate) || learningRate <= 0) {
      throw new Error("Enter a DiT path and valid epochs, rank, and learning rate.");
    }
    const blocks = trainingArchitecture === "MiniMax H3" && trainingBlocksSwap.trim() === "auto" ? "auto" : Number(trainingBlocksSwap);
    if (blocks !== "auto" && (!Number.isInteger(blocks) || blocks < 0)) throw new Error("Blocks to swap must be a non-negative number or auto.");
    return {
      architecture: trainingArchitecture,
      dataset_config: config,
      dit: trainingDit.trim(),
      output_dir: trainingOutputDir.trim() || "output_loras",
      output_name: trainingOutputName.trim() || "fizgig_lora",
      vae: trainingVae.trim(),
      text_encoder: trainingTextEncoder.trim(),
      network_dim: rank,
      network_alpha: rank,
      learning_rate: learningRate,
      max_train_epochs: epochs,
      save_every_n_epochs: 0,
      blocks_to_swap: blocks,
      gradient_checkpointing: true,
      sample_prompts: samplePromptFile,
      sample_every_n_epochs: Number(sampleEveryEpochs) || 0,
      sample_at_first: sampleAtFirst,
      sample_width: Number(sampleWidth) || 768,
      sample_height: Number(sampleHeight) || 768,
      sample_steps: Number(sampleSteps) || 8,
      sample_seed: Number(sampleSeed) || 42,
      prepare_cache: true,
    } as const;
  }

  async function saveSamplePrompts() {
    setLoading(true);
    setError("");
    try {
      const result = await writeSamplePrompts(sampleName.trim() || "prompts.txt", sampleText);
      setSamplePromptFile(result.relative_path);
      setMessage(`Saved ${result.count} sample prompt${result.count === 1 ? "" : "s"} to ${result.relative_path}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save sample prompts");
      setMessage("Sample prompt save failed");
    } finally {
      setLoading(false);
    }
  }

  async function activateSampleOverride() {
    setLoading(true);
    setError("");
    try {
      const result = await writeSampleOverride({
        output_dir: trainingOutputDir.trim() || "output_loras",
        prompt: sampleOverridePrompt,
        seed: Number(sampleSeed) || 1234,
        width: Number(sampleWidth) || 768,
        height: Number(sampleHeight) || 768,
      });
      setMessage(`Live sample override active at ${result.relative_path}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to activate sample override");
      setMessage("Sample override failed");
    } finally {
      setLoading(false);
    }
  }

  async function deactivateSampleOverride() {
    try {
      await clearSampleOverride(trainingOutputDir.trim() || "output_loras");
      setMessage("Live sample override cleared");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to clear sample override");
    }
  }

  async function previewProfiler() {
    setLoading(true); setError("");
    try {
      const result = await previewProfile({ lora: profilerLora.trim(), output: profilerOutput.trim(), krea2: true });
      setProfilerPreview(result); setMessage("Profiler command validated; nothing has started");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to validate profiler"); setMessage("Profiler validation failed"); }
    finally { setLoading(false); }
  }

  async function runProfiler() {
    if (!window.confirm("Start the profiler job now?")) return;
    setLoading(true); setError("");
    try {
      const started = await startProfile({ lora: profilerLora.trim(), output: profilerOutput.trim(), krea2: true });
      let job = started;
      while (["queued", "starting", "running", "cancel_requested"].includes(job.status)) { setMessage(`${job.message} · ${Math.round(job.progress)}%`); await new Promise((resolve) => window.setTimeout(resolve, 700)); job = await getJob(started.id); }
      if (job.status !== "completed") throw new Error(job.error || `Profiler ${job.status}`);
      setMessage("Profiler completed; open the generated HTML report");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to run profiler"); setMessage("Profiler failed"); }
    finally { setLoading(false); }
  }

  async function previewExtractor() {
    setLoading(true); setError("");
    try {
      const result = await previewExtract({ source: extractSource.trim(), output: extractOutput.trim(), samples: Number(extractSamples) || 0, rank: Number(extractRank) || 2 });
      setExtractPreview(result); setMessage("Extraction command validated; nothing has started");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to validate extraction"); setMessage("Extraction validation failed"); }
    finally { setLoading(false); }
  }

  async function runExtractor() {
    if (!window.confirm("Start LoRA extraction now?")) return;
    setLoading(true); setError("");
    try {
      const started = await startExtract({ source: extractSource.trim(), output: extractOutput.trim(), samples: Number(extractSamples) || 0, rank: Number(extractRank) || 2 });
      let job = started;
      while (["queued", "starting", "running", "cancel_requested"].includes(job.status)) { setMessage(`${job.message} · ${Math.round(job.progress)}%`); await new Promise((resolve) => window.setTimeout(resolve, 700)); job = await getJob(started.id); }
      if (job.status !== "completed") throw new Error(job.error || `Extraction ${job.status}`);
      setMessage("LoRA extraction completed");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to run extraction"); setMessage("Extraction failed"); }
    finally { setLoading(false); }
  }

  async function inspectMetadataFile() {
    setLoading(true); setError("");
    try { setMetadataResult(await inspectMetadata(metadataPath.trim())); setMessage("SafeTensors metadata loaded without loading tensor data"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to inspect metadata"); setMessage("Metadata inspection failed"); }
    finally { setLoading(false); }
  }

  async function loadRepairState() {
    setLoading(true); setError("");
    try {
      const result = await loadRepairDefaultState(repairFamily);
      setRepairStateJson(JSON.stringify(result.state, null, 2));
      setMessage(`${repairFamily} slider state loaded`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load Repair Studio state"); setMessage("Repair state failed"); }
    finally { setLoading(false); }
  }

  function repairValues() {
    let state: Record<string, unknown>;
    try { state = JSON.parse(repairStateJson) as Record<string, unknown>; }
    catch { throw new Error("Slider state must be valid JSON."); }
    if (!state || Array.isArray(state)) throw new Error("Slider state must be a JSON object.");
    return { primary: repairPrimary.trim(), donor: repairDonor.trim(), output: repairOutput.trim(), state };
  }

  function updateRepairBlock(blockId: string, field: "primary_strength" | "donor_strength" | "primary_enabled" | "donor_enabled", value: number | boolean) {
    try {
      const state = JSON.parse(repairStateJson) as { blocks?: Record<string, Record<string, unknown>> };
      const blocks = state.blocks ?? {};
      blocks[blockId] = { primary_enabled: true, primary_strength: 1, donor_enabled: true, donor_strength: 0, ...(blocks[blockId] ?? {}), [field]: value };
      setRepairStateJson(JSON.stringify({ ...state, blocks }, null, 2));
    } catch {
      setError("Load a valid slider state before editing individual blocks.");
    }
  }

  async function previewRepair() {
    setLoading(true); setError("");
    try { setRepairPreview(await previewRepairBake(repairValues())); setMessage("Repair bake validated; nothing has started"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to validate repair bake"); setMessage("Repair validation failed"); }
    finally { setLoading(false); }
  }

  function repairRenderValues() {
    return { ...repairValues(), output: repairPreviewOutput.trim(), family: repairFamily, dit: trainingDit.trim(), vae: trainingVae.trim(), text_encoder: trainingTextEncoder.trim(), blocks_to_swap: Number(trainingBlocksSwap) || 0 };
  }

  async function previewRepairRenderJob() {
    setLoading(true); setError("");
    try { setRepairRenderPreview(await previewRepairRender(repairRenderValues())); setMessage("Repair render validated; no model weights loaded"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to validate repair render"); setMessage("Repair render validation failed"); }
    finally { setLoading(false); }
  }

  async function runRepairRender() {
    if (!window.confirm("Start a GPU Repair Studio preview now?")) return;
    setLoading(true); setError("");
    try {
      const started = await startRepairRender(repairRenderValues());
      let job = started;
      while (["queued", "starting", "running", "cancel_requested"].includes(job.status)) { setMessage(`${job.message} · ${Math.round(job.progress)}%`); await new Promise((resolve) => window.setTimeout(resolve, 900)); job = await getJob(started.id); }
      if (job.status !== "completed") throw new Error(job.error || `Repair render ${job.status}`);
      setMessage(`Repair preview saved to ${String((job.result as { output_relative_path?: string })?.output_relative_path || repairPreviewOutput)}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to render Repair Studio preview"); setMessage("Repair render failed"); }
    finally { setLoading(false); }
  }

  async function runRepair() {
    if (!window.confirm("Bake this repaired LoRA now?")) return;
    setLoading(true); setError("");
    try {
      const started = await startRepairBake(repairValues());
      let job = started;
      while (["queued", "starting", "running", "cancel_requested"].includes(job.status)) { setMessage(`${job.message} · ${Math.round(job.progress)}%`); await new Promise((resolve) => window.setTimeout(resolve, 700)); job = await getJob(started.id); }
      if (job.status !== "completed") throw new Error(job.error || `Repair bake ${job.status}`);
      setMessage("Repair bake completed");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to bake repaired LoRA"); setMessage("Repair bake failed"); }
    finally { setLoading(false); }
  }

  async function savePreferences() {
    setLoading(true); setError("");
    try {
      await updateWorkspaceState({
        training_dit: trainingDit.trim(), training_vae: trainingVae.trim(),
        training_text_encoder: trainingTextEncoder.trim(), training_output_dir: trainingOutputDir.trim(),
      });
      setMessage("Preferences saved to the shared workspace state");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to save preferences"); setMessage("Preferences save failed"); }
    finally { setLoading(false); }
  }

  async function scanExplorer() {
    setLoading(true); setError("");
    try { const result = await loadLoraExplorer(catalogFolder.trim()); setExplorerItems(result.items); setMessage(`Found ${result.items.length} LoRA file${result.items.length === 1 ? "" : "s"}`); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to scan LoRAs"); setMessage("Explorer scan failed"); }
    finally { setLoading(false); }
  }

  async function scanRoyale() {
    setLoading(true); setError("");
    try { const result = await loadLoraRoyale(catalogFolder.trim()); setRoyaleItems(result.items); setMessage(`Found ${result.items.length} checkpoint${result.items.length === 1 ? "" : "s"}`); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to scan checkpoints"); setMessage("Royale scan failed"); }
    finally { setLoading(false); }
  }

  function catalogModels() {
    if (!trainingDit.trim() || !trainingVae.trim() || !trainingTextEncoder.trim()) throw new Error("Set DiT, VAE, and text encoder paths in Preferences first.");
    return { dit: trainingDit.trim(), vae: trainingVae.trim(), text_encoder: trainingTextEncoder.trim() };
  }

  async function runExplorerRender() {
    setLoading(true); setError("");
    try {
      const state = JSON.parse(repairStateJson) as Record<string, unknown>;
      const started = await startExplorerRender({ family: catalogFamily, primary: catalogPrimary.trim(), output_dir: `${catalogOutput.trim() || "out/workbench"}/explorer`, state, ...catalogModels(), variants: 4, intensity: 0.5, structure: 1 });
      let job = started;
      while (["queued", "starting", "running", "cancel_requested"].includes(job.status)) { setMessage(`${job.message} · ${Math.round(job.progress)}%`); await new Promise((resolve) => window.setTimeout(resolve, 900)); job = await getJob(started.id); }
      if (job.status !== "completed") throw new Error(job.error || `Explorer render ${job.status}`);
      setMessage("Explorer variants completed; download them from the output folder");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to render Explorer variants"); setMessage("Explorer render failed"); }
    finally { setLoading(false); }
  }

  async function runRoyaleRender() {
    setLoading(true); setError("");
    try {
      const started = await startRoyaleRender({ family: catalogFamily, folder: catalogFolder.trim(), output_dir: `${catalogOutput.trim() || "out/workbench"}/royale`, prompt: catalogPrompt, seed: 42, width: 512, height: 512, max_checkpoints: 32, ...catalogModels() });
      let job = started;
      while (["queued", "starting", "running", "cancel_requested"].includes(job.status)) { setMessage(`${job.message} · ${Math.round(job.progress)}%`); await new Promise((resolve) => window.setTimeout(resolve, 900)); job = await getJob(started.id); }
      if (job.status !== "completed") throw new Error(job.error || `Royale render ${job.status}`);
      setMessage("Royale sequence completed; download the rendered checkpoints");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to render Royale sequence"); setMessage("Royale render failed"); }
    finally { setLoading(false); }
  }

  async function previewTraining() {
    setLoading(true);
    setError("");
    try {
      const result = await previewTrainingCommand(launchValues());
      setTrainingCommand(result);
      setMessage("Training command validated; nothing has started");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to validate training command");
      setMessage("Training validation failed");
    } finally {
      setLoading(false);
    }
  }

  async function startTraining() {
    if (!window.confirm("Start the model training job now? This will use the configured worker/GPU.")) return;
    setLoading(true);
    setError("");
    try {
      const started = await startTrainingJob(launchValues());
      let job = started;
      while (["queued", "starting", "running", "cancel_requested"].includes(job.status)) {
        setMessage(`${job.message} · ${Math.round(job.progress)}%`);
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        job = await getJob(started.id);
      }
      if (job.status !== "completed") throw new Error(job.error || `Training ${job.status}`);
      setMessage("Training completed; see the job log in .fizgig/jobs/");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to start training");
      setMessage("Training failed");
    } finally {
      setLoading(false);
    }
  }

  async function refreshPresets(architecture: string) {
    try {
      const result = await listPresets(architecture);
      setPresetNames(result.names);
      setSelectedPreset(result.names[0] ?? "");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load presets");
    }
  }

  async function openPreset(name: string) {
    setSelectedPreset(name);
    if (!name) return;
    try {
      const values = await loadPreset(trainingArchitecture, name);
      setPresetName(name);
      setPresetJson(`${JSON.stringify(values, null, 2)}\n`);
      setMessage(`Loaded preset ${name}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load preset");
    }
  }

  async function persistPreset() {
    const name = presetName.trim();
    if (!name) {
      setError("Enter a preset name first.");
      return;
    }
    let values: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(presetJson);
      if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") throw new Error("Preset must be a JSON object");
      values = parsed as Record<string, unknown>;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Preset JSON is invalid");
      return;
    }
    const overwrite = presetNames.includes(name) && window.confirm(`Overwrite preset “${name}”?`);
    if (presetNames.includes(name) && !overwrite) return;
    try {
      await savePreset(trainingArchitecture, name, values, overwrite);
      await refreshPresets(trainingArchitecture);
      setSelectedPreset(name);
      setMessage(`Saved preset ${name}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save preset");
    }
  }

  async function removePreset() {
    if (!selectedPreset || !window.confirm(`Delete preset “${selectedPreset}”?`)) return;
    try {
      await deletePreset(trainingArchitecture, selectedPreset);
      await refreshPresets(trainingArchitecture);
      setPresetName("");
      setPresetJson("{}\n");
      setMessage(`Deleted preset ${selectedPreset}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to delete preset");
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
        if (typeof result.values.training_dit === "string") setTrainingDit(result.values.training_dit);
        if (typeof result.values.training_vae === "string") setTrainingVae(result.values.training_vae);
        if (typeof result.values.training_text_encoder === "string") setTrainingTextEncoder(result.values.training_text_encoder);
        if (typeof result.values.training_output_dir === "string" && result.values.training_output_dir.trim()) setTrainingOutputDir(result.values.training_output_dir);
      })
      .catch(() => {
        // The UI remains usable with defaults while an older API is restarting.
      });
  }, []);

  useEffect(() => {
    let disposed = false;
    async function refreshJobs() {
      try { const result = await listJobs(); if (!disposed) setJobs(result.jobs); } catch { /* API may be restarting */ }
    }
    void refreshJobs();
    const timer = window.setInterval(refreshJobs, 2000);
    return () => { disposed = true; window.clearInterval(timer); };
  }, []);

  useEffect(() => {
    void refreshPresets(trainingArchitecture);
  }, [trainingArchitecture]);

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
                  {!["start", "prep", "captions", "samples", "training", "profiler", "repair", "explorer", "royale", "extract", "metadata", "preferences"].includes(section.key) && <span className="soon-dot" />}
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
              architecture={trainingArchitecture}
              setArchitecture={setTrainingArchitecture}
              presetNames={presetNames}
              selectedPreset={selectedPreset}
              onSelectPreset={openPreset}
              presetName={presetName}
              setPresetName={setPresetName}
              presetJson={presetJson}
              setPresetJson={setPresetJson}
              onSavePreset={persistPreset}
              onDeletePreset={removePreset}
              dit={trainingDit}
              setDit={setTrainingDit}
              vae={trainingVae}
              setVae={setTrainingVae}
              textEncoder={trainingTextEncoder}
              setTextEncoder={setTrainingTextEncoder}
              outputDir={trainingOutputDir}
              setOutputDir={setTrainingOutputDir}
              outputName={trainingOutputName}
              setOutputName={setTrainingOutputName}
              epochs={trainingEpochs}
              setEpochs={setTrainingEpochs}
              rank={trainingRank}
              setRank={setTrainingRank}
              learningRate={trainingLearningRate}
              setLearningRate={setTrainingLearningRate}
              blocksSwap={trainingBlocksSwap}
              setBlocksSwap={setTrainingBlocksSwap}
              command={trainingCommand}
              onPreview={previewTraining}
              onStart={startTraining}
            />
          )}
          {active === "samples" && (
            <SamplesPage
              text={sampleText}
              setText={setSampleText}
              name={sampleName}
              setName={setSampleName}
              promptFile={samplePromptFile}
              everyEpochs={sampleEveryEpochs}
              setEveryEpochs={setSampleEveryEpochs}
              atFirst={sampleAtFirst}
              setAtFirst={setSampleAtFirst}
              width={sampleWidth}
              setWidth={setSampleWidth}
              height={sampleHeight}
              setHeight={setSampleHeight}
              steps={sampleSteps}
              setSteps={setSampleSteps}
              seed={sampleSeed}
              setSeed={setSampleSeed}
              overridePrompt={sampleOverridePrompt}
              setOverridePrompt={setSampleOverridePrompt}
              outputDir={trainingOutputDir}
              loading={loading}
              onSave={saveSamplePrompts}
              onActivate={activateSampleOverride}
              onDeactivate={deactivateSampleOverride}
            />
          )}
          {active === "profiler" && <ToolPage title="Profiler" eyebrow="WORKBENCH / PROFILE" description="Generate a Krea 2 weight-only HTML report from a LoRA." source={profilerLora} setSource={setProfilerLora} output={profilerOutput} setOutput={setProfilerOutput} sourceLabel="LoRA file" preview={profilerPreview} loading={loading} onPreview={previewProfiler} onStart={runProfiler} />}
          {active === "repair" && <RepairPage family={repairFamily} setFamily={setRepairFamily} primary={repairPrimary} setPrimary={setRepairPrimary} donor={repairDonor} setDonor={setRepairDonor} output={repairOutput} setOutput={setRepairOutput} previewOutput={repairPreviewOutput} setPreviewOutput={setRepairPreviewOutput} dit={trainingDit} vae={trainingVae} textEncoder={trainingTextEncoder} stateJson={repairStateJson} setStateJson={setRepairStateJson} onBlockChange={updateRepairBlock} preview={repairPreview} renderPreview={repairRenderPreview} loading={loading} onLoadState={loadRepairState} onPreview={previewRepair} onStart={runRepair} onRenderPreview={previewRepairRenderJob} onRender={runRepairRender} />}
          {active === "extract" && <ToolPage title="Extract" eyebrow="TOOLS / EXTRACT" description="Extract a lower-rank LoRA with the existing Fizgig SVD engine." source={extractSource} setSource={setExtractSource} output={extractOutput} setOutput={setExtractOutput} sourceLabel="Source LoRA" extra={<><label className="prep-control"><span>Samples (0 = weight-only)</span><input type="number" min="0" value={extractSamples} onChange={(event) => setExtractSamples(event.target.value)} /></label><label className="prep-control"><span>Target rank</span><input type="number" min="1" value={extractRank} onChange={(event) => setExtractRank(event.target.value)} /></label></>} preview={extractPreview} loading={loading} onPreview={previewExtractor} onStart={runExtractor} />}
          {active === "metadata" && <MetadataPage path={metadataPath} setPath={setMetadataPath} result={metadataResult} loading={loading} onInspect={inspectMetadataFile} />}
          {active === "preferences" && <PreferencesPage dit={trainingDit} setDit={setTrainingDit} vae={trainingVae} setVae={setTrainingVae} textEncoder={trainingTextEncoder} setTextEncoder={setTrainingTextEncoder} outputDir={trainingOutputDir} setOutputDir={setTrainingOutputDir} loading={loading} onSave={savePreferences} />}
          {active === "explorer" && <CatalogPage title="LoRA Explorer" description="Browse workspace LoRAs, inspect metadata, and render guided variants from the current Repair Studio state." folder={catalogFolder} setFolder={setCatalogFolder} items={explorerItems} mode="explorer" loading={loading} onScan={scanExplorer} family={catalogFamily} setFamily={setCatalogFamily} primary={catalogPrimary} setPrimary={setCatalogPrimary} prompt={catalogPrompt} setPrompt={setCatalogPrompt} output={catalogOutput} setOutput={setCatalogOutput} onRender={runExplorerRender} />}
          {active === "royale" && <CatalogPage title="LoRA Royale" description="Scan epoch checkpoints, render the sequence with one resident engine, and download the generated frames." folder={catalogFolder} setFolder={setCatalogFolder} items={royaleItems} mode="royale" loading={loading} onScan={scanRoyale} family={catalogFamily} setFamily={setCatalogFamily} primary={catalogPrimary} setPrimary={setCatalogPrimary} prompt={catalogPrompt} setPrompt={setCatalogPrompt} output={catalogOutput} setOutput={setCatalogOutput} onRender={runRoyaleRender} />}
          {active === "jobs" && <JobsPage jobs={jobs} onCancel={async (id) => { try { await cancelJob(id); const result = await listJobs(); setJobs(result.jobs); setMessage("Cancellation requested"); } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to cancel job"); } }} />}
          {active !== "start" && active !== "captions" && active !== "prep" && active !== "training" && active !== "samples" && active !== "profiler" && active !== "repair" && active !== "extract" && active !== "metadata" && active !== "preferences" && active !== "explorer" && active !== "royale" && active !== "jobs" && <ComingSoonPage section={active} />}
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
  architecture: string;
  setArchitecture: (value: string) => void;
  presetNames: string[];
  selectedPreset: string;
  onSelectPreset: (value: string) => void;
  presetName: string;
  setPresetName: (value: string) => void;
  presetJson: string;
  setPresetJson: (value: string) => void;
  onSavePreset: () => void;
  onDeletePreset: () => void;
  dit: string;
  setDit: (value: string) => void;
  vae: string;
  setVae: (value: string) => void;
  textEncoder: string;
  setTextEncoder: (value: string) => void;
  outputDir: string;
  setOutputDir: (value: string) => void;
  outputName: string;
  setOutputName: (value: string) => void;
  epochs: string;
  setEpochs: (value: string) => void;
  rank: string;
  setRank: (value: string) => void;
  learningRate: string;
  setLearningRate: (value: string) => void;
  blocksSwap: string;
  setBlocksSwap: (value: string) => void;
  command: TrainingCommandPreview | null;
  onPreview: () => void;
  onStart: () => void;
}) {
  return <>
    <section className="card prep-banner training-banner">
      <div><div className="section-kicker">TRAINING / DATASET CONTRACT</div><h2>Build a compatible training config</h2><p>These values write the same TOML dataset contract used by Fizgig’s existing training scripts. Actual model jobs will attach to this config through the durable job runner.</p></div>
      <span className="pill accent">CONFIG ONLY</span>
    </section>
    <section className="card prep-options">
      <div className="section-heading"><div><div className="section-kicker">DATASET CONFIGURATION</div><h3>{props.folder || "No folder selected"}</h3></div><span className="pill">FIZGIG_TRAIN.TOML</span></div>
      <div className="training-form-grid">
        <label className="prep-control"><span>Model family</span><select value={props.architecture} onChange={(event) => props.setArchitecture(event.target.value)}><option>Flux 2 Klein Base 9B</option><option>Krea 2</option><option>MiniMax H3</option></select></label>
        <label className="prep-control"><span>Config name</span><input value={props.configName} onChange={(event) => props.setConfigName(event.target.value)} placeholder="Fizgig_train" /></label>
        <label className="prep-control"><span>Target megapixels</span><select value={props.megapixels} onChange={(event) => props.setMegapixels(event.target.value)}><option value="0.25">0.25 MP</option><option value="0.5">0.5 MP</option><option value="0.75">0.75 MP</option><option value="1.0">1.0 MP</option><option value="1.5">1.5 MP</option><option value="2.0">2.0 MP</option></select></label>
        <label className="prep-control"><span>Batch size</span><input type="number" min="1" max="1024" value={props.batchSize} onChange={(event) => props.setBatchSize(event.target.value)} /></label>
      </div>
      <div className="training-checks"><label><input type="checkbox" checked={props.enableBucket} onChange={(event) => props.setEnableBucket(event.target.checked)} /> Enable resolution buckets</label><label><input type="checkbox" checked={props.noUpscale} onChange={(event) => props.setNoUpscale(event.target.checked)} /> Never upscale images</label></div>
      <div className="prep-actions"><button className="button primary" disabled={props.loading || !props.folder} onClick={props.onSave}>{props.loading ? "Saving…" : "Save dataset config"}<span>✓</span></button><span className="helper-text">Dataset folder is selected on Start. Save this contract before validating a model launch.</span></div>
    </section>
    <section className="card prep-options">
      <div className="section-heading"><div><div className="section-kicker">TRAINING LAUNCH</div><h3>Connect model files and runtime settings</h3></div><span className="pill">COMMAND PREVIEW FIRST</span></div>
      <div className="training-form-grid">
        <label className="prep-control"><span>DiT model path</span><input value={props.dit} onChange={(event) => props.setDit(event.target.value)} placeholder="/models/base.safetensors" /></label>
        <label className="prep-control"><span>VAE path <small>(required for cache)</small></span><input value={props.vae} onChange={(event) => props.setVae(event.target.value)} placeholder="/models/vae.safetensors" /></label>
        <label className="prep-control"><span>Text encoder path <small>(required for cache)</small></span><input value={props.textEncoder} onChange={(event) => props.setTextEncoder(event.target.value)} placeholder="/models/text_encoder.safetensors" /></label>
        <label className="prep-control"><span>Output directory</span><input value={props.outputDir} onChange={(event) => props.setOutputDir(event.target.value)} placeholder="output_loras" /></label>
        <label className="prep-control"><span>Output name</span><input value={props.outputName} onChange={(event) => props.setOutputName(event.target.value)} /></label>
        <label className="prep-control"><span>Epochs</span><input type="number" min="1" value={props.epochs} onChange={(event) => props.setEpochs(event.target.value)} /></label>
        <label className="prep-control"><span>LoRA rank</span><input type="number" min="1" value={props.rank} onChange={(event) => props.setRank(event.target.value)} /></label>
        <label className="prep-control"><span>Learning rate</span><input value={props.learningRate} onChange={(event) => props.setLearningRate(event.target.value)} /></label>
        <label className="prep-control"><span>Blocks to swap <small>(MiniMax accepts auto)</small></span><input value={props.blocksSwap} onChange={(event) => props.setBlocksSwap(event.target.value)} /></label>
      </div>
      <div className="prep-actions"><button className="button ghost" disabled={props.loading} onClick={props.onPreview}>Validate command</button><button className="button primary" disabled={props.loading || !props.command} onClick={props.onStart}>Start training <span>→</span></button><span className="helper-text">Validation only reads paths and builds argv. Start is the explicit model-job action.</span></div>
      {props.command && <div className="command-preview"><div className="section-kicker">VALIDATED PIPELINE</div>{props.command.stages.map((stage) => <div key={stage.name}><small>{stage.name}</small><pre>{stage.shell_command}</pre></div>)}<small>Working directory: {props.command.working_directory}</small></div>}
    </section>
    <section className="card preset-workspace">
      <div className="section-heading"><div><div className="section-kicker">CUSTOM PRESETS / {props.architecture}</div><h3>Save and restore training values</h3></div><span className="pill">DESKTOP COMPATIBLE</span></div>
      <div className="preset-toolbar"><select value={props.selectedPreset} onChange={(event) => void props.onSelectPreset(event.target.value)}><option value="">Select a saved preset…</option>{props.presetNames.map((name) => <option key={name}>{name}</option>)}</select><button className="button ghost small" disabled={!props.selectedPreset} onClick={props.onDeletePreset}>Delete</button></div>
      <div className="preset-save-row"><input value={props.presetName} onChange={(event) => props.setPresetName(event.target.value)} placeholder="Preset name" /><button className="button ghost small" onClick={props.onSavePreset}>Save preset</button></div>
      <textarea className="preset-json" value={props.presetJson} onChange={(event) => props.setPresetJson(event.target.value)} spellCheck={false} aria-label="Preset JSON values" />
      <div className="helper-text">The JSON body stores the same named-value map used by the desktop preset repository. Model-specific validation will be added before training launch.</div>
    </section>
    <section className="card config-preview"><div className="section-heading"><div><div className="section-kicker">GENERATED ARTIFACT</div><h3>{props.result?.config_relative_path ?? "No config saved yet"}</h3></div></div>{props.result ? <pre>{props.result.content}</pre> : <EmptyState text="Save the configuration to generate a compatible TOML file." />}</section>
  </>;
}

function SamplesPage(props: {
  text: string;
  setText: (value: string) => void;
  name: string;
  setName: (value: string) => void;
  promptFile: string;
  everyEpochs: string;
  setEveryEpochs: (value: string) => void;
  atFirst: boolean;
  setAtFirst: (value: boolean) => void;
  width: string;
  setWidth: (value: string) => void;
  height: string;
  setHeight: (value: string) => void;
  steps: string;
  setSteps: (value: string) => void;
  seed: string;
  setSeed: (value: string) => void;
  overridePrompt: string;
  setOverridePrompt: (value: string) => void;
  outputDir: string;
  loading: boolean;
  onSave: () => void;
  onActivate: () => void;
  onDeactivate: () => void;
}) {
  return <>
    <section className="card prep-banner">
      <div><div className="section-kicker">SAMPLES / TRAINING PREVIEWS</div><h2>Control preview prompts without touching the model</h2><p>Prompt files and live overrides use the same artifacts consumed by the desktop trainer. Saving prompts does not start inference.</p></div>
      <span className="pill accent">NO MODEL REQUIRED</span>
    </section>
    <section className="card prep-options">
      <div className="section-heading"><div><div className="section-kicker">PROMPT FILE</div><h3>One prompt per line</h3></div><span className="pill">DESKTOP COMPATIBLE</span></div>
      <div className="preset-save-row"><input value={props.name} onChange={(event) => props.setName(event.target.value)} placeholder="prompts.txt" /><span className="helper-text">Saved under samples/</span></div>
      <textarea className="preset-json sample-prompts" value={props.text} onChange={(event) => props.setText(event.target.value)} aria-label="Sample prompts" />
      <div className="prep-actions"><button className="button primary" disabled={props.loading} onClick={props.onSave}>Save prompt file <span>✓</span></button><span className="helper-text">{props.promptFile ? `Training can use ${props.promptFile}` : "No prompt file saved yet"}</span></div>
    </section>
    <section className="card prep-options">
      <div className="section-heading"><div><div className="section-kicker">PREVIEW SETTINGS</div><h3>Cadence and canvas</h3></div></div>
      <div className="training-form-grid sample-settings-grid">
        <label className="prep-control"><span>Every N epochs</span><input type="number" min="0" value={props.everyEpochs} onChange={(event) => props.setEveryEpochs(event.target.value)} /></label>
        <label className="prep-control"><span>Width</span><input type="number" min="16" value={props.width} onChange={(event) => props.setWidth(event.target.value)} /></label>
        <label className="prep-control"><span>Height</span><input type="number" min="16" value={props.height} onChange={(event) => props.setHeight(event.target.value)} /></label>
        <label className="prep-control"><span>Steps</span><input type="number" min="1" value={props.steps} onChange={(event) => props.setSteps(event.target.value)} /></label>
        <label className="prep-control"><span>Seed</span><input type="number" value={props.seed} onChange={(event) => props.setSeed(event.target.value)} /></label>
      </div>
      <label className="training-checks"><input type="checkbox" checked={props.atFirst} onChange={(event) => props.setAtFirst(event.target.checked)} /> Sample at the start of training</label>
    </section>
    <section className="card prep-options">
      <div className="section-heading"><div><div className="section-kicker">LIVE OVERRIDE</div><h3>Change the next preview at an epoch boundary</h3></div><span className="pill">OUTPUT: {props.outputDir || "output_loras"}</span></div>
      <label className="editor-label" style={{ marginTop: 18 }}>Temporary prompt<textarea value={props.overridePrompt} onChange={(event) => props.setOverridePrompt(event.target.value)} placeholder="Leave empty to disable prompt override." /></label>
      <div className="prep-actions"><button className="button primary" disabled={props.loading || !props.overridePrompt.trim()} onClick={props.onActivate}>Activate override</button><button className="button ghost" disabled={props.loading} onClick={props.onDeactivate}>Clear override</button><span className="helper-text">The trainer reads this file between epochs; the current run is not interrupted.</span></div>
    </section>
  </>;
}

function RepairPage(props: {
  family: string;
  setFamily: (value: string) => void;
  primary: string;
  setPrimary: (value: string) => void;
  donor: string;
  setDonor: (value: string) => void;
  output: string;
  setOutput: (value: string) => void;
  previewOutput: string;
  setPreviewOutput: (value: string) => void;
  dit: string;
  vae: string;
  textEncoder: string;
  stateJson: string;
  setStateJson: (value: string) => void;
  onBlockChange: (blockId: string, field: "primary_strength" | "donor_strength" | "primary_enabled" | "donor_enabled", value: number | boolean) => void;
  preview: { operation: string; primary: string; donor: string; output: string; execution_ready: boolean } | null;
  renderPreview: { operation: string; family: string; output: string; execution_ready: boolean } | null;
  loading: boolean;
  onLoadState: () => void;
  onPreview: () => void;
  onStart: () => void;
  onRenderPreview: () => void;
  onRender: () => void;
}) {
  return <>
    <section className="card prep-banner"><div><div className="section-kicker">WORKBENCH / REPAIR STUDIO</div><h2>Bake a repaired LoRA</h2><p>Edit the existing Fizgig slider state as JSON, validate all workspace paths, and run the desktop-compatible bake operation as a durable browser job.</p></div><span className="pill accent">BAKE JOB</span></section>
    <section className="card prep-options"><div className="section-heading"><div><div className="section-kicker">INPUT / OUTPUT</div><h3>Configure repair sources</h3></div><span className="pill">WORKSPACE-SAFE OUTPUT</span></div>
      <div className="training-form-grid"><label className="prep-control"><span>Model family</span><select value={props.family} onChange={(event) => props.setFamily(event.target.value)}><option value="klein">Flux Klein 9B</option><option value="krea2">Krea 2</option><option value="h3">MiniMax H3</option></select></label><label className="prep-control"><span>Primary LoRA</span><input value={props.primary} onChange={(event) => props.setPrimary(event.target.value)} placeholder="output_loras/primary.safetensors" /></label><label className="prep-control"><span>Optional donor LoRA</span><input value={props.donor} onChange={(event) => props.setDonor(event.target.value)} placeholder="output_loras/donor.safetensors" /></label><label className="prep-control"><span>Baked LoRA output</span><input value={props.output} onChange={(event) => props.setOutput(event.target.value)} /></label><label className="prep-control"><span>DiT model</span><input value={props.dit} readOnly placeholder="Set in Preferences" /></label><label className="prep-control"><span>VAE model</span><input value={props.vae} readOnly placeholder="Set in Preferences" /></label><label className="prep-control"><span>Text encoder</span><input value={props.textEncoder} readOnly placeholder="Set in Preferences" /></label><label className="prep-control"><span>Preview image output</span><input value={props.previewOutput} onChange={(event) => props.setPreviewOutput(event.target.value)} /></label></div>
      <div className="prep-actions"><button className="button ghost" disabled={props.loading} onClick={props.onLoadState}>Load default sliders</button><span className="helper-text">GPU preview rendering will be attached as a separate stage; this action only writes the repaired SafeTensors file.</span></div>
    </section>
    <section className="card prep-options"><div className="section-heading"><div><div className="section-kicker">SLIDER STATE</div><h3>Block controls</h3></div><span className="pill">DESKTOP COMPATIBLE</span></div><RepairBlockGrid stateJson={props.stateJson} onChange={props.onBlockChange} /><details className="advanced-state"><summary>Advanced JSON state</summary><textarea className="code-editor" value={props.stateJson} onChange={(event) => props.setStateJson(event.target.value)} spellCheck={false} rows={18} /></details><div className="prep-actions"><button className="button ghost" disabled={props.loading} onClick={props.onPreview}>Validate bake</button><button className="button primary" disabled={props.loading || !props.preview} onClick={props.onStart}>Bake repaired LoRA <span>→</span></button></div>{props.preview && <div className="command-preview"><div className="section-kicker">VALIDATED OPERATION</div><pre>{JSON.stringify(props.preview, null, 2)}</pre><small>Validation checked input existence, slider schema, and workspace-safe output.</small></div>}</section>
    <section className="card prep-options"><div className="section-heading"><div><div className="section-kicker">GPU PREVIEW</div><h3>Render the current slider state</h3></div><span className="pill accent">MODEL JOB</span></div><p className="helper-text">Preview uses the selected model family and the paths saved in Preferences. Validation never loads weights.</p><div className="prep-actions"><button className="button ghost" disabled={props.loading} onClick={props.onRenderPreview}>Validate render</button><button className="button primary" disabled={props.loading || !props.renderPreview} onClick={props.onRender}>Render preview <span>→</span></button></div>{props.renderPreview && <div className="command-preview"><div className="section-kicker">VALIDATED RENDER</div><pre>{JSON.stringify(props.renderPreview, null, 2)}</pre></div>}</section>
  </>;
}

function RepairBlockGrid(props: { stateJson: string; onChange: (blockId: string, field: "primary_strength" | "donor_strength" | "primary_enabled" | "donor_enabled", value: number | boolean) => void }) {
  let blocks: Record<string, { primary_enabled?: boolean; primary_strength?: number; donor_enabled?: boolean; donor_strength?: number }> = {};
  try {
    const parsed = JSON.parse(props.stateJson) as { blocks?: Record<string, { primary_enabled?: boolean; primary_strength?: number; donor_enabled?: boolean; donor_strength?: number }> };
    blocks = parsed.blocks ?? {};
  } catch {
    return <div className="empty-state repair-empty">Enter valid JSON or load a default slider state.</div>;
  }
  const entries = Object.entries(blocks);
  if (entries.length === 0) return <div className="empty-state repair-empty">Load default sliders to edit the block grid.</div>;
  return <div className="repair-grid">{entries.map(([blockId, block]) => <div className="repair-block" key={blockId}><div className="repair-block-title"><strong>{blockId.replace("_", " ")}</strong><span>{block.primary_enabled === false ? "off" : "on"}</span></div><label><input type="checkbox" checked={block.primary_enabled !== false} onChange={(event) => props.onChange(blockId, "primary_enabled", event.target.checked)} /> Primary</label><input className="repair-range" type="range" min="-3" max="3" step="0.05" value={block.primary_strength ?? 1} onChange={(event) => props.onChange(blockId, "primary_strength", Number(event.target.value))} /><output>{Number(block.primary_strength ?? 1).toFixed(2)}</output><label><input type="checkbox" checked={block.donor_enabled !== false} onChange={(event) => props.onChange(blockId, "donor_enabled", event.target.checked)} /> Donor</label><input className="repair-range donor" type="range" min="-3" max="3" step="0.05" value={block.donor_strength ?? 0} onChange={(event) => props.onChange(blockId, "donor_strength", Number(event.target.value))} /><output>{Number(block.donor_strength ?? 0).toFixed(2)}</output></div>)}</div>;
}

function ToolPage(props: {
  title: string;
  eyebrow: string;
  description: string;
  source: string;
  setSource: (value: string) => void;
  sourceLabel: string;
  output: string;
  setOutput: (value: string) => void;
  extra?: ReactNode;
  preview: WorkbenchPreview | null;
  loading: boolean;
  onPreview: () => void;
  onStart: () => void;
}) {
  return <>
    <section className="card prep-banner"><div><div className="section-kicker">{props.eyebrow}</div><h2>{props.title}</h2><p>{props.description}</p></div><span className="pill accent">DURABLE JOB</span></section>
    <section className="card prep-options"><div className="section-heading"><div><div className="section-kicker">INPUT / OUTPUT</div><h3>Configure the tool</h3></div><span className="pill">WORKSPACE-SAFE OUTPUT</span></div>
      <div className="training-form-grid"><label className="prep-control"><span>{props.sourceLabel}</span><input value={props.source} onChange={(event) => props.setSource(event.target.value)} placeholder="/models/subject.safetensors" /></label><label className="prep-control"><span>Output path</span><input value={props.output} onChange={(event) => props.setOutput(event.target.value)} /></label>{props.extra}</div>
      <div className="prep-actions"><button className="button ghost" disabled={props.loading} onClick={props.onPreview}>Validate command</button><button className="button primary" disabled={props.loading || !props.preview} onClick={props.onStart}>Start job <span>→</span></button><span className="helper-text">The first validation only checks files and builds argv. It does not load model weights.</span></div>
      {props.preview && <div className="command-preview"><div className="section-kicker">VALIDATED COMMAND</div><pre>{props.preview.shell_command}</pre><small>Working directory: {props.preview.working_directory}</small></div>}
    </section>
  </>;
}

function MetadataPage(props: { path: string; setPath: (value: string) => void; result: MetadataInspection | null; loading: boolean; onInspect: () => void }) {
  return <>
    <section className="card prep-banner"><div><div className="section-kicker">TOOLS / METADATA</div><h2>Inspect a SafeTensors file</h2><p>Read the header, model metadata, tensor names, dtypes, and shapes without loading model weights.</p></div><span className="pill accent">READ ONLY</span></section>
    <section className="card prep-options"><div className="field-row"><label className="path-field"><span className="field-icon">⌁</span><input value={props.path} onChange={(event) => props.setPath(event.target.value)} placeholder="output_loras/model.safetensors" /></label><button className="button primary" disabled={props.loading || !props.path.trim()} onClick={props.onInspect}>Inspect <span>→</span></button></div></section>
    {props.result && <><div className="metric-grid"><Metric label="File size" value={`${(props.result.size_bytes / 1024 / 1024).toFixed(1)} MB`} tone="blue" /><Metric label="Tensors" value={String(props.result.tensor_count)} tone="green" /><Metric label="Metadata fields" value={String(Object.keys(props.result.metadata).length)} tone="amber" /></div><section className="card config-preview"><div className="section-heading"><div><div className="section-kicker">MODEL METADATA</div><h3>{props.result.relative_path || props.result.path}</h3></div></div><pre>{JSON.stringify(props.result.metadata, null, 2)}</pre></section><section className="card table-card"><div className="section-heading"><div><div className="section-kicker">TENSOR INDEX</div><h3>Header entries</h3></div></div><div className="table-wrap"><table><thead><tr><th>Name</th><th>dtype</th><th>shape</th><th>offsets</th></tr></thead><tbody>{props.result.tensors.map((tensor) => <tr key={tensor.name}><td>{tensor.name}</td><td>{tensor.dtype}</td><td>{JSON.stringify(tensor.shape)}</td><td>{JSON.stringify(tensor.data_offsets)}</td></tr>)}</tbody></table></div></section></>}
  </>;
}

function PreferencesPage(props: { dit: string; setDit: (value: string) => void; vae: string; setVae: (value: string) => void; textEncoder: string; setTextEncoder: (value: string) => void; outputDir: string; setOutputDir: (value: string) => void; loading: boolean; onSave: () => void }) {
  return <>
    <section className="card prep-banner"><div><div className="section-kicker">TOOLS / PREFERENCES</div><h2>Keep remote paths in one place</h2><p>These values are saved in the workspace state and reused by Training, Samples, Profiler, and other browser surfaces.</p></div><span className="pill accent">PERSISTED</span></section>
    <section className="card prep-options"><div className="section-heading"><div><div className="section-kicker">MODEL FILES</div><h3>Mounted model paths</h3></div><span className="pill">SERVER-SIDE PATHS</span></div><div className="training-form-grid"><label className="prep-control"><span>DiT model</span><input value={props.dit} onChange={(event) => props.setDit(event.target.value)} placeholder="/models/base.safetensors" /></label><label className="prep-control"><span>VAE</span><input value={props.vae} onChange={(event) => props.setVae(event.target.value)} placeholder="/models/vae.safetensors" /></label><label className="prep-control"><span>Text encoder</span><input value={props.textEncoder} onChange={(event) => props.setTextEncoder(event.target.value)} placeholder="/models/text_encoder.safetensors" /></label><label className="prep-control"><span>Default output directory</span><input value={props.outputDir} onChange={(event) => props.setOutputDir(event.target.value)} /></label></div><div className="prep-actions"><button className="button primary" disabled={props.loading} onClick={props.onSave}>Save preferences <span>✓</span></button><span className="helper-text">The browser cannot read your PC filesystem directly; these paths must exist in the server or Modal workspace.</span></div></section>
  </>;
}

function CatalogPage(props: { title: string; description: string; folder: string; setFolder: (value: string) => void; items: LoraCatalogItem[]; mode: "explorer" | "royale"; loading: boolean; onScan: () => void; family: string; setFamily: (value: string) => void; primary: string; setPrimary: (value: string) => void; prompt: string; setPrompt: (value: string) => void; output: string; setOutput: (value: string) => void; onRender: () => void }) {
  return <><section className="card prep-banner"><div><div className="section-kicker">WORKBENCH / {props.mode.toUpperCase()}</div><h2>{props.title}</h2><p>{props.description}</p></div><span className="pill accent">CATALOG</span></section><section className="card prep-options"><div className="field-row"><label className="path-field"><span className="field-icon">⌁</span><input value={props.folder} onChange={(event) => props.setFolder(event.target.value)} placeholder="output_loras" /></label><button className="button primary" disabled={props.loading || !props.folder.trim()} onClick={props.onScan}>Scan <span>→</span></button></div><div className="training-form-grid catalog-render-form"><label className="prep-control"><span>Family</span><select value={props.family} onChange={(event) => props.setFamily(event.target.value)}><option value="klein">Flux Klein 9B</option><option value="krea2">Krea 2</option><option value="h3">MiniMax H3</option></select></label>{props.mode === "explorer" && <label className="prep-control"><span>Primary LoRA</span><input value={props.primary} onChange={(event) => props.setPrimary(event.target.value)} placeholder="output_loras/model.safetensors" /></label>}<label className="prep-control"><span>Prompt</span><input value={props.prompt} onChange={(event) => props.setPrompt(event.target.value)} /></label><label className="prep-control"><span>Rendered output folder</span><input value={props.output} onChange={(event) => props.setOutput(event.target.value)} /></label></div><div className="prep-actions"><button className="button ghost" disabled={props.loading || (props.mode === "explorer" && !props.primary.trim())} onClick={props.onRender}>{props.mode === "explorer" ? "Render variants" : "Render sequence"} <span>→</span></button><span className="helper-text">Model paths come from Preferences. GPU work continues as a durable job after refresh.</span></div></section><section className="card table-card"><div className="section-heading"><div><div className="section-kicker">CHECKPOINT INVENTORY</div><h3>{props.items.length} files</h3></div></div>{props.items.length === 0 ? <EmptyState text="Scan a workspace folder to list SafeTensors checkpoints." /> : <div className="table-wrap"><table><thead><tr><th>{props.mode === "royale" ? "Epoch / label" : "Name"}</th><th>Path</th><th>Size</th><th>{props.mode === "explorer" ? "Tensors" : "Status"}</th><th /></tr></thead><tbody>{props.items.map((item) => <tr key={item.relative_path}><td>{item.label ?? item.name}</td><td><a className="file-link" href={artifactDownloadUrl(item.relative_path)}>{item.relative_path}</a></td><td>{(item.size_bytes / 1024 / 1024).toFixed(1)} MB</td><td>{props.mode === "explorer" ? (item.tensor_count ?? "—") : <span className="caption-state ready">Ready to render</span>}</td><td><a className="row-action" href={artifactDownloadUrl(item.relative_path)}>Download</a></td></tr>)}</tbody></table></div>}</section></>;
}

function JobsPage(props: { jobs: import("./api").JobRecord[]; onCancel: (id: string) => void }) {
  const active = props.jobs.filter((job) => ["queued", "starting", "running", "cancel_requested"].includes(job.status));
  return <><section className="card prep-banner"><div><div className="section-kicker">WORKSPACE / JOBS</div><h2>Durable work queue</h2><p>Jobs are persisted in the workspace, so refreshing or reconnecting the browser does not lose their state.</p></div><span className="pill accent">{active.length} ACTIVE</span></section><section className="card table-card"><div className="section-heading"><div><div className="section-kicker">RECENT OPERATIONS</div><h3>{props.jobs.length} jobs</h3></div></div>{props.jobs.length === 0 ? <EmptyState text="No browser jobs have run yet." /> : <div className="table-wrap"><table><thead><tr><th>Operation</th><th>Status</th><th>Progress</th><th>Message</th><th /></tr></thead><tbody>{props.jobs.map((job) => <tr key={job.id}><td><strong>{job.kind}</strong><small className="job-id">{job.id}</small></td><td><span className={`caption-state ${job.status === "completed" ? "ready" : job.status === "failed" ? "missing" : ""}`}>{job.status}</span></td><td><div className="job-progress"><span style={{ width: `${Math.max(0, Math.min(100, job.progress))}%` }} /></div>{Math.round(job.progress)}%</td><td>{job.error || job.message}</td><td>{["queued", "starting", "running", "cancel_requested"].includes(job.status) && <button className="row-action" onClick={() => props.onCancel(job.id)}>Cancel</button>}{job.result != null && <><ArtifactLinks value={job.result} /><pre className="job-result">{JSON.stringify(job.result, null, 2)}</pre></>}</td></tr>)}</tbody></table></div>}</section></>;
}

function ArtifactLinks({ value }: { value: unknown }) {
  const paths: string[] = [];
  function collect(item: unknown) { if (Array.isArray(item)) item.forEach(collect); else if (item && typeof item === "object") Object.entries(item).forEach(([key, child]) => key.endsWith("path") && typeof child === "string" ? paths.push(child) : collect(child)); }
  collect(value);
  const unique = Array.from(new Set(paths));
  return unique.length ? <div className="artifact-links">{unique.map((path) => <span className="artifact-item" key={path}><ArtifactPreview path={path} /><a className="row-action" href={artifactDownloadUrl(path)}>Download {path.split("/").pop()}</a></span>)}</div> : null;
}

function ArtifactPreview({ path }: { path: string }) {
  const lower = path.toLowerCase();
  const url = artifactDownloadUrl(path);
  if (/\.(png|jpe?g|webp|gif)$/.test(lower)) return <a href={url} target="_blank" rel="noreferrer"><img className="artifact-thumb" src={url} alt={path} /></a>;
  if (/\.(mp4|webm|mov)$/.test(lower)) return <video className="artifact-thumb" src={url} controls preload="metadata" />;
  if (/\.(wav|mp3|flac|m4a|ogg)$/.test(lower)) return <audio className="artifact-audio" src={url} controls preload="metadata" />;
  return null;
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
  const labels: Record<SectionKey, string> = { start: "Start", prep: "Image Prep", captions: "Captions", samples: "Samples", training: "Training", profiler: "Profiler", repair: "Repair Studio", explorer: "LoRA Explorer", royale: "LoRA Royale", extract: "Extract", metadata: "Metadata", preferences: "Preferences", jobs: "Jobs" };
  return <section className="card rollout-card"><div className="rollout-icon">✦</div><div className="pill accent">CONTROLLED ROLLOUT</div><h2>{labels[section]} is next</h2><p>The browser shell is in place. This surface will be wired to the existing Fizgig engine behind a durable API and job contract before controls are enabled.</p><div className="rollout-rule"><span>Current milestone</span><strong>Start + Captions vertical slice</strong></div></section>;
}

function EmptyState({ text, large = false }: { text: string; large?: boolean }) {
  return <div className={`empty-state ${large ? "large" : ""}`}><div className="empty-icon">◌</div><span>{text}</span></div>;
}

export default App;
