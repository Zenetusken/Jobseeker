#!/bin/bash
# vLLM Engine Startup Script
# Launches Foundation-Sec-8B-Reasoning with AWQ 4-bit quantization
# Strict 8.4GB VRAM partition via --gpu-memory-utilization 0.7

set -e

echo "=== Jobseeker vLLM Engine ==="
echo "Model: ${VLLM_MODEL_NAME:-fdtn-ai/Foundation-Sec-8B-Reasoning}"
echo "Quantization: ${VLLM_QUANTIZATION:-awq}"
echo "Max Model Length: ${VLLM_MAX_MODEL_LEN:-4096}"
echo "GPU Memory Utilization: ${VLLM_GPU_MEMORY_UTILIZATION:-0.7}"
echo "=============================="

python -m vllm.entrypoints.openai.api_server \
    --model "${VLLM_MODEL_NAME:-fdtn-ai/Foundation-Sec-8B-Reasoning}" \
    --quantization "${VLLM_QUANTIZATION:-awq}" \
    --max-model-len "${VLLM_MAX_MODEL_LEN:-4096}" \
    --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTILIZATION:-0.7}" \
    --enforce-eager \
    --host 0.0.0.0 \
    --port 8000
