<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import FFT from "fft.js";

const props = defineProps<{ stationKey: string; location: string; channel: string }>();
const specCanvas = ref<HTMLCanvasElement>();
const waveCanvas = ref<HTMLCanvasElement>();
const dataBuffer: number[] = [];
let samplesSinceLastRender = 0;
let socket: WebSocket | undefined;
let spectrogramFloor: number | undefined;
let spectrogramCeiling: number | undefined;

const N = 512;
const fft = new FFT(N);
const fftOutput = fft.createComplexArray();

const getJetColor = (value: number) => {
  const v = Math.max(0, Math.min(1, value));
  const channel = (offset: number) => Math.floor(255 * Math.max(0, Math.min(1, 1.5 - Math.abs(v * 4 - offset))));
  return `rgb(${channel(3)},${channel(2)},${channel(1)})`;
};

const computeFft = () => {
  const samples = dataBuffer.slice(-N);
  samples.unshift(...new Array(N - samples.length).fill(0));
  const input = samples.map((sample, index) => sample * 0.5 * (1 - Math.cos((2 * Math.PI * index) / (N - 1))));
  fft.realTransform(fftOutput, input);
  fft.completeSpectrum(fftOutput);
  return Array.from({ length: N / 2 }, (_, index) => {
    const real = fftOutput[index * 2];
    const imaginary = fftOutput[index * 2 + 1];
    return 20 * Math.log10(Math.sqrt(real * real + imaginary * imaginary) + 1e-6);
  });
};

const drawSpectrogramColumn = () => {
  const canvas = specCanvas.value;
  const context = canvas?.getContext("2d");
  if (!canvas || !context || dataBuffer.length < N) return;
  context.drawImage(canvas, 1, 0, canvas.width - 1, canvas.height, 0, 0, canvas.width - 1, canvas.height);
  const values = computeFft();
  const binHeight = canvas.height / values.length;
  const sortedValues = [...values].sort((left, right) => left - right);
  let nextFloor = sortedValues[Math.floor(sortedValues.length * 0.1)] - 5;
  let nextCeiling = sortedValues[Math.floor(sortedValues.length * 0.98)] + 5;
  if (nextCeiling - nextFloor < 40) {
    const center = (nextFloor + nextCeiling) / 2;
    nextFloor = center - 20;
    nextCeiling = center + 20;
  }
  spectrogramFloor = spectrogramFloor === undefined ? nextFloor : spectrogramFloor * 0.92 + nextFloor * 0.08;
  spectrogramCeiling = spectrogramCeiling === undefined ? nextCeiling : spectrogramCeiling * 0.92 + nextCeiling * 0.08;
  values.forEach((db, index) => {
    context.fillStyle = getJetColor((db - spectrogramFloor!) / (spectrogramCeiling! - spectrogramFloor!));
    context.fillRect(canvas.width - 1, canvas.height - (index + 1) * binHeight, 1, binHeight + 0.5);
  });
};

const redrawWaveform = () => {
  const canvas = waveCanvas.value;
  const context = canvas?.getContext("2d");
  if (!canvas || !context || dataBuffer.length === 0) return;
  const center = canvas.height / 2;
  context.fillStyle = "#05070a";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.strokeStyle = "#243b5a";
  context.beginPath();
  context.moveTo(0, center);
  context.lineTo(canvas.width, center);
  context.stroke();
  const scale = Math.max(Number.EPSILON, ...dataBuffer.map(Math.abs)) * 1.15;
  const samplesPerPixel = 23;
  const pixels = Math.min(canvas.width, Math.ceil(dataBuffer.length / samplesPerPixel));
  context.fillStyle = "#64b5f6";
  for (let pixel = 0; pixel < pixels; pixel += 1) {
    const start = Math.max(0, dataBuffer.length - (pixels - pixel) * samplesPerPixel);
    const values = dataBuffer.slice(start, start + samplesPerPixel);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const top = center - (max / scale) * center;
    const bottom = center - (min / scale) * center;
    context.fillRect(canvas.width - pixels + pixel, top, 1, Math.max(1.5, bottom - top));
  }
};

const sizeCanvases = async () => {
  await nextTick();
  for (const [canvas, height] of [[waveCanvas.value, 116], [specCanvas.value, 116]] as const) {
    if (!canvas) continue;
    canvas.width = canvas.getBoundingClientRect().width || 768;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (context) {
      context.fillStyle = "#05070a";
      context.fillRect(0, 0, canvas.width, canvas.height);
    }
  }
};

const connect = () => {
  socket?.close();
  dataBuffer.splice(0);
  samplesSinceLastRender = 0;
  spectrogramFloor = undefined;
  spectrogramCeiling = undefined;
  socket = new WebSocket("wss://ws-nexaseis.domiko.dev");
  socket.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      const station = message?.station;
      if (!station || props.stationKey !== `${station.network || ""}.${station.code || ""}.${station.location || ""}` || props.location !== (station.location || "") || props.channel !== (station.channel || "")) return;
      const signal: unknown[] = Array.isArray(message.waveform) ? message.waveform : [];
      const valid = signal.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
      dataBuffer.push(...valid);
      dataBuffer.splice(0, Math.max(0, dataBuffer.length - 18400));
      samplesSinceLastRender += valid.length;
      redrawWaveform();
      while (samplesSinceLastRender >= 23) {
        drawSpectrogramColumn();
        samplesSinceLastRender -= 23;
      }
    } catch (error) {
      console.error("WS error:", error);
    }
  };
};

onMounted(() => { void sizeCanvases(); connect(); });
watch(() => [props.stationKey, props.location, props.channel], connect);
onBeforeUnmount(() => socket?.close());
</script>

<template>
  <div class="station-visualizer">
    <div class="visualizer-canvas waveform"><canvas ref="waveCanvas" /></div>
    <div class="visualizer-canvas spectrogram"><canvas ref="specCanvas" /></div>
  </div>
</template>
