# Mahsoul AI Agriculture Platform — Backend

Production-ready FastAPI backend for AI-powered farm assistance.

## Architecture at a Glance

```
Request → FastAPI → Route → Service → ModelLoader (singleton) → TF Model
                                   → RAGService  → Embedder + Retriever
                                   → AssistantService → LLM (future)
```

## Project Structure

```
smart_cactus/
├── app/
│   ├── main.py                    ← FastAPI app, middleware, lifespan
│   ├── core/
│   │   ├── config.py              ← Pydantic-settings, all env vars
│   │   ├── logging.py             ← Structured JSON logging
│   │   └── dependencies.py        ← FastAPI dependency providers
│   ├── api/v1/
│   │   ├── disease_routes.py      ← POST /api/v1/disease/predict
│   │   ├── assistant_routes.py    ← POST /api/v1/assistant/chat
│   │   └── rag_routes.py          ← POST /api/v1/rag/query
│   ├── services/
│   │   ├── disease_service.py     ← Prediction pipeline
│   │   ├── assistant_service.py   ← LLM chat (placeholder)
│   │   └── rag_service.py         ← RAG pipeline (placeholder)
│   ├── models/ml/
│   │   ├── model_loader.py        ← TF singleton loader
│   │   ├── mahsoul_production_model.h5   ← YOUR MODEL (place here)
│   │   └── class_indices.json            ← YOUR CLASS MAP (place here)
│   ├── schemas/
│   │   ├── disease_schema.py
│   │   ├── assistant_schema.py
│   │   └── rag_schema.py
│   ├── utils/
│   │   ├── image_preprocessing.py ← Albumentations-matching pipeline
│   │   └── gpu_utils.py
│   └── rag/
│       ├── retriever.py           ← ChromaDB / Mock retriever
│       └── embeddings.py          ← SentenceTransformer / Mock embedder
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Quickstart

### 1. Place your model files

```
app/models/ml/mahsoul_production_model.h5
app/models/ml/class_indices.json
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env as needed
```

### 3. Install & run locally

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Run with Docker (CPU)

```bash
docker compose up --build
```

### 5. Run with Docker (GPU)

```bash
# Requires: nvidia-container-toolkit installed on host
# Change Dockerfile FROM line to: tensorflow/tensorflow:2.17.0-gpu
docker compose up --build
```

---

## API Reference

Interactive docs: `http://localhost:8000/docs`

### Health Check

```
GET /health
```

Response:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "model_loaded": true,
    "model_name": "Mahsoul_Ensemble_v3",
    "classes": 10,
    "gpu": { "available": true, "count": 1 },
    "version": "1.0.0"
  },
  "error": null
}
```

### Disease Prediction

```
POST /api/v1/disease/predict
Content-Type: multipart/form-data
```

Response:
```json
{
  "success": true,
  "prediction": {
    "disease": "Tomato___Late_blight",
    "confidence": 0.94,
    "top_predictions": [
      { "disease": "Tomato___Late_blight",  "confidence": 0.94 },
      { "disease": "Tomato___Early_blight", "confidence": 0.03 },
      { "disease": "Tomato___healthy",       "confidence": 0.02 }
    ],
    "all_scores": {
      "Tomato___healthy":      0.02,
      "Tomato___Early_blight": 0.03,
      "Tomato___Late_blight":  0.94
    }
  },
  "model": "Mahsoul_Ensemble_v3",
  "error": null
}
```

### AI Farm Assistant Chat

```
POST /api/v1/assistant/chat
Content-Type: application/json
```

### RAG Knowledge Base Query

```
POST /api/v1/rag/query
Content-Type: application/json
```

---

## curl Examples

### Health check

```bash
curl http://localhost:8000/health
```

### Predict disease

```bash
curl -X POST http://localhost:8000/api/v1/disease/predict \
  -F "file=@/path/to/tomato_leaf.jpg"
```

### Assistant chat

```bash
curl -X POST http://localhost:8000/api/v1/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "My tomato plants have dark spots on the leaves. What disease is this?",
    "conversation_history": [],
    "context": { "location": "Cairo", "crop": "tomato" }
  }'
```

### RAG query

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the symptoms of late blight in tomatoes?",
    "top_k": 5
  }'
```

---

## Flutter Integration

### HTTP client setup (`pubspec.yaml`)

```yaml
dependencies:
  dio: ^5.7.0
  http: ^1.2.0
```

### Disease prediction service (`lib/services/disease_api.dart`)

```dart
import 'dart:io';
import 'package:dio/dio.dart';

class DiseaseApiService {
  final Dio _dio;

  DiseaseApiService({String baseUrl = 'http://YOUR_SERVER_IP:8000'})
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(seconds: 60),
        ));

  Future<DiseaseResult> predictDisease(File imageFile) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        imageFile.path,
        filename: imageFile.path.split('/').last,
      ),
    });

    final response = await _dio.post('/api/v1/disease/predict', data: formData);

    if (response.data['success'] == true) {
      return DiseaseResult.fromJson(response.data['prediction']);
    }
    throw Exception(response.data['error'] ?? 'Prediction failed');
  }
}

class DiseaseResult {
  final String disease;
  final double confidence;
  final List<TopPrediction> topPredictions;
  final Map<String, double> allScores;

  DiseaseResult({
    required this.disease,
    required this.confidence,
    required this.topPredictions,
    required this.allScores,
  });

  factory DiseaseResult.fromJson(Map<String, dynamic> json) {
    return DiseaseResult(
      disease: json['disease'] as String,
      confidence: (json['confidence'] as num).toDouble(),
      topPredictions: (json['top_predictions'] as List)
          .map((e) => TopPrediction.fromJson(e as Map<String, dynamic>))
          .toList(),
      allScores: Map<String, double>.from(
        (json['all_scores'] as Map).map(
          (k, v) => MapEntry(k as String, (v as num).toDouble()),
        ),
      ),
    );
  }
}

class TopPrediction {
  final String disease;
  final double confidence;

  TopPrediction({required this.disease, required this.confidence});

  factory TopPrediction.fromJson(Map<String, dynamic> json) => TopPrediction(
        disease: json['disease'] as String,
        confidence: (json['confidence'] as num).toDouble(),
      );
}
```

### Usage in a Flutter widget

```dart
// Pick image and call API
final picker = ImagePicker();
final picked = await picker.pickImage(source: ImageSource.camera);
if (picked == null) return;

setState(() => _isLoading = true);
try {
  final service = DiseaseApiService(baseUrl: 'http://YOUR_SERVER_IP:8000');
  final result = await service.predictDisease(File(picked.path));

  setState(() {
    _disease = result.disease;
    _confidence = result.confidence;
    _topPredictions = result.topPredictions;
  });
} catch (e) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Error: $e')),
  );
} finally {
  setState(() => _isLoading = false);
}
```

---

## Activating Future Services

### 1. Enable RAG (vector search)

```bash
# In requirements.txt, uncomment:
# chromadb==0.5.23
# sentence-transformers==3.3.0

pip install chromadb sentence-transformers

# In .env:
VECTOR_DB_URL=http://localhost:8001
```

Then uncomment the `chromadb` service in `docker-compose.yml`.

### 2. Enable LLM (farm assistant)

```bash
# In .env:
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o
```

Then replace `_placeholder_response` in `assistant_service.py` with a real OpenAI/Anthropic call.

---

## Image Preprocessing Details

The preprocessing **exactly matches** the Albumentations training pipeline:

| Step | Operation |
|------|-----------|
| 1 | Load → convert to RGB |
| 2 | Resize to 224×224 (LANCZOS) |
| 3 | Cast to float32 |
| 4 | Scale: `img / 255.0` |
| 5 | Normalize: `(img - mean) / std` where `mean=(0.485,0.456,0.406)` `std=(0.229,0.224,0.225)` |
| 6 | Expand dims: `(1, 224, 224, 3)` |
