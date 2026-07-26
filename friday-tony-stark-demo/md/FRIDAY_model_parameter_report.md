# Báo cáo thông số mô hình FRIDAY

> **Thời điểm kiểm tra:** 22/07/2026  
> **Phạm vi:** cấu hình runtime hiện tại của `friday-tony-stark-demo`, gồm Ollama local và các model được gọi qua API.  
> **Bảo mật:** báo cáo không chứa API key, mật khẩu, URL cơ sở dữ liệu hoặc token.

## Kết luận nhanh

FRIDAY không phải một mô hình đơn lẻ. Đây là một hệ thống agent điều phối nhiều model local và remote, vì vậy không tồn tại một con số tham số duy nhất có thể cộng chính xác cho toàn bộ hệ thống.

| Cách tính | Kết quả hợp lý | Ý nghĩa |
|---|---:|---|
| Neural weights chạy **local** | **xấp xỉ 4.30B** | Gemma 3 `4.3B` + Silero VAD khoảng `260K` |
| Tổng từng phần có kích thước công khai | **xấp xỉ 12.30B** | Local ở trên + Llama 3.1 `8B` chạy từ xa qua Groq |
| Tổng end-to-end của mọi provider | **Không xác định** | Gemini, Sarvam và OpenAI không cung cấp số tham số có thể kiểm chứng trong tài liệu sản phẩm đã rà soát |

Nếu cần một câu trả lời ngắn gọn để giới thiệu dự án:

> **FRIDAY hiện chạy khoảng 4.3 tỷ tham số neural ngay trên máy. Hệ thống còn điều phối các model cloud; riêng phần model có kích thước được công khai đạt khoảng 12.3 tỷ tham số, nhưng đây không phải một model ghép 12.3B và không phải tổng tuyệt đối của toàn hệ thống.**

![Phạm vi tham số có thể kiểm chứng](assets/friday_model_parameters/02_parameter_scope.png)

## Ollama local

Hai lệnh được dùng để đọc metadata thực tế trên máy:

```powershell
ollama list
ollama show gemma3:4b
```

Kết quả chính:

| Thuộc tính | Giá trị hiện tại |
|---|---:|
| Model | `gemma3:4b` |
| Ollama model ID | `a2af6cc3eb7f` |
| Architecture | `gemma3` |
| Parameters | **`4.3B`** |
| Quantization | `Q4_K_M` |
| Dung lượng model trên máy | `3.3 GB` |
| Context length | `131,072` token |
| Embedding length | `2,560` |
| Capability | `completion`, `vision` |

![Thông số Gemma 3 trong Ollama](assets/friday_model_parameters/03_ollama_gemma3_spec.png)

Tên tag `4b` là tên nhóm model, còn manifest Ollama đang cài báo `4.3B`. Vì vậy báo cáo dùng con số `4.3B` thay vì làm tròn xuống `4.0B`.

`Q4_K_M` là dạng lượng tử hóa. Nó giảm số bit dùng để lưu và tính toán mỗi trọng số, nhờ đó model chỉ chiếm khoảng `3.3 GB`; nó **không làm giảm số lượng tham số** từ 4.3B xuống một con số khác.

Thông số 128K context và khả năng nhận ảnh cũng phù hợp với [Gemma 3 Model Card chính thức của Google](https://ai.google.dev/gemma/docs/core/model_card_3).

## Bản đồ runtime

![Bản đồ model runtime của FRIDAY](assets/friday_model_parameters/01_runtime_architecture.png)

Model không được gọi đồng thời trong mọi yêu cầu. Router của FRIDAY chọn model và công cụ theo loại tác vụ: hội thoại, nghe giọng nói, phát giọng nói, tìm kiếm hoặc hiểu màn hình.

### Thành phần local

| Thành phần | Vai trò | Tham số | Trạng thái tính |
|---|---|---:|---|
| Ollama `gemma3:4b` | Vision và hiểu nội dung màn hình | khoảng **4.3B** | Tính vào local |
| Silero VAD | Phát hiện đoạn có giọng nói | khoảng **260K** | Tính vào local |
| Hash embedding 128 chiều | Vector tìm kiếm theo thuật toán hash | `0` learned params | Không phải neural model |
| Keyword overlap reranker | Xếp hạng theo từ khóa | `0` learned params | Không phải neural model |
| Neural Network Visual | Hiệu ứng node và ánh sáng trên UI | `0` learned params | Chỉ là đồ họa |

Silero được nạp tại [`server/agent_runtime/friday_agent.py`](../server/agent_runtime/friday_agent.py) bằng `silero.VAD.load()`. Môi trường hiện cài `livekit-plugins-silero==1.5.1` và chứa model ONNX khoảng `2.33 MB`. Dự án Silero công bố model VAD hiện tại có [khoảng 260K tham số](https://github.com/snakers4/silero-vad/wiki/Version-history-and-Available-Models), vì vậy số này được ghi là xấp xỉ.

Gemma local được chọn bởi `FRIDAY_VISION_MODEL` trong [`screen_understanding.py`](../friday/app/computer/service/screen_understanding.py).

### Thành phần remote

| Luồng | Model/provider hiện tại | Nơi chạy | Tham số công khai |
|---|---|---|---:|
| LLM chính của voice agent | Gemini 2.5 Flash | Google API | Không xác định |
| Speech-to-text chính | Sarvam `saaras:v3` | Sarvam API | Không xác định |
| Text-to-speech chính | Sarvam `bulbul:v3` | Sarvam API | Không xác định |
| STT refiner | Groq `llama-3.1-8b-instant` | Groq API | **8B danh nghĩa** |
| TTS cho PageClient/Desktop | OpenAI `tts-1` | OpenAI API | Không xác định |
| Agent service fallback | `gpt-4o-mini` | OpenAI-compatible API | Không xác định |
| Desktop STT fallback | `gpt-4o-mini-transcribe` | OpenAI-compatible API | Không xác định |
| Live Search fallback | Gemini 2.0 Flash | Google API | Không xác định |

Cấu hình provider chính nằm tại [`server/agent_runtime/providers.py`](../server/agent_runtime/providers.py). STT refiner nằm tại [`friday/refiner/stt_corrector.py`](../friday/refiner/stt_corrector.py), còn TTS giao diện nằm tại [`friday/app/agent_console/tts_service.py`](../friday/app/agent_console/tts_service.py).

Meta công bố Llama 3.1 gồm các bản 8B, 70B và 405B; model refiner của FRIDAY là bản 8B theo [Llama 3.1 Model Card](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md). Model này chạy trên Groq, không được lưu trong repository và không chiếm 8B weights trên máy của người dùng.

Trang model chính thức xác nhận mã `gemini-2.5-flash` và khả năng của model nhưng không nêu số tham số: [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash). Tương tự, tài liệu API xác nhận `tts-1` là model speech hợp lệ nhưng không cung cấp parameter count: [OpenAI Audio API](https://platform.openai.com/docs/api-reference/audio/createSpeech).

## Công thức tính

### 1. Neural parameters chạy local

```text
P_local ≈ P_Gemma3 + P_SileroVAD
        ≈ 4.3B + 0.00026B
        ≈ 4.30026B
        ≈ 4.30B tham số
```

Con số `4.30026B` chỉ là phép cộng theo metadata đã được làm tròn của Ollama và ước lượng Silero. Không nên trình bày nó như một phép đếm chính xác đến từng trọng số.

### 2. Tổng từng phần có kích thước công khai

```text
P_known ≈ P_local + P_Llama3.1_refiner
        ≈ 4.30026B + 8B
        ≈ 12.30026B
        ≈ 12.30B tham số
```

`12.30B` là tổng kiểm kê của các model biết kích thước. Nó **không** có nghĩa FRIDAY là một model 12.3B, không phản ánh lượng VRAM cần cho một lần chạy, và không phải tất cả model đều hoạt động đồng thời.

### 3. Tổng toàn hệ thống

```text
P_end_to_end = P_known
             + P_Gemini
             + P_Sarvam_STT
             + P_Sarvam_TTS
             + P_OpenAI_TTS
             + các model route-specific khác

P_end_to_end = không xác định từ dữ liệu công khai hiện có
```

## Những thứ không được tính là tham số

- Số file Python, số dòng code hoặc số node/edge trong CodeGraph.
- Bảng PostgreSQL/Supabase, dữ liệu hội thoại và ảnh chụp màn hình.
- Prompt, Markdown giới thiệu FRIDAY và tài liệu huấn luyện chưa được đóng gói thành checkpoint.
- Context length `131,072` và embedding length `2,560`.
- 33 node cùng các dây nối trong `NeuralNetworkVisual`.
- Kích thước file model `3.3 GB`.
- Hash embedding, keyword matching và các rule-based intent.

![Neural visualization được render từ UI hiện tại](assets/friday_model_parameters/04_neural_ui_visualization.png)

Ảnh trên được render trực tiếp từ [`neural_network_visual.py`](../friday/src/UI/static/desktop_ui/widgets/neural_network_visual.py). Đây là biểu diễn trạng thái listening/thinking/speaking của FRIDAY, không phải sơ đồ topology thật của Gemma 3 và không mang trọng số học máy.

## Thành phần tùy chọn chưa tính

Source có adapter cho `sentence-transformers/all-MiniLM-L6-v2` trong [`vector_embedder.py`](../friday/core/vector/vector_embedder.py), nhưng đợt kiểm tra này không thấy runtime hiện tại khởi tạo adapter đó. Vì thế báo cáo loại model này khỏi tổng hiện hành. Nếu sau này chuyển từ hash embedding sang SentenceTransformer, cần thêm parameter count của checkpoint thực sự được tải.

Quét repository cũng không thấy checkpoint riêng dạng `.gguf`, `.safetensors`, `.onnx`, `.pt` hoặc `.pth` ngoài dependency trong `.venv`. Ollama quản lý Gemma ở model store riêng bên ngoài source tree.

## Lưu ý cấu hình

`GOOGLE_SEARCH_MODEL` hiện có fallback là `gemini-2.0-flash`. Theo [Gemini API changelog](https://ai.google.dev/gemini-api/docs/changelog), dòng Gemini 2.0 Flash đã có lịch ngừng phục vụ ngày 01/06/2026. Đây không làm thay đổi phép tính tham số, nhưng nên đổi Live Search sang model còn được hỗ trợ để tránh lỗi provider.

## Cách cập nhật báo cáo sau này

1. Chạy `ollama list` và `ollama show <model>` để lấy metadata local mới.
2. Kiểm tra `.env` theo **tên biến**, không đưa secret vào báo cáo.
3. Đối chiếu model name trong source và tài liệu chính thức của provider.
4. Chỉ cộng model có parameter count được công bố hoặc đo trực tiếp từ checkpoint.
5. Ghi riêng local, remote và optional; không gộp chúng thành kích thước của một model duy nhất.
6. Chạy lại script tạo hình:

```powershell
uv run python md/generate_model_report_figures.py
```

## Nguồn chính

- [Google Gemma 3 Model Card](https://ai.google.dev/gemma/docs/core/model_card_3)
- [Meta Llama 3.1 Model Card](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md)
- [Silero VAD - Version history and available models](https://github.com/snakers4/silero-vad/wiki/Version-history-and-Available-Models)
- [Google Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash)
- [Google Gemini API changelog](https://ai.google.dev/gemini-api/docs/changelog)
- [OpenAI Audio API](https://platform.openai.com/docs/api-reference/audio/createSpeech)

---

**Kết luận cuối:** mô hình neural local của FRIDAY hiện ở quy mô **xấp xỉ 4.3B tham số**. Khi ghi nhận thêm model remote có kích thước công khai là Llama 3.1 8B, phần kiểm kê biết được đạt **xấp xỉ 12.3B**. Tổng thật của toàn bộ agent không thể xác định trung thực cho đến khi các provider đóng công bố kiến trúc hoặc parameter count tương ứng.
