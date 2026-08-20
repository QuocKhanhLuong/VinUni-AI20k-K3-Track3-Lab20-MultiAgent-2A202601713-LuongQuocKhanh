# Lab Guide: Multi-Agent Research System

## Scenario

Bạn cần xây dựng một research assistant có thể nhận câu hỏi dài, tìm thông tin, phân tích và viết câu trả lời cuối cùng. Lab yêu cầu so sánh hai cách làm:

1. **Single-agent baseline**: một agent làm toàn bộ.
2. **Multi-agent workflow**: Supervisor điều phối Researcher, Analyst, Writer.

## Quy tắc quan trọng

- Không thêm agent nếu không có lý do rõ ràng.
- Mỗi agent phải có responsibility riêng.
- Shared state phải đủ rõ để debug.
- Phải có trace hoặc log cho từng bước.
- Phải benchmark, không chỉ nhìn output bằng cảm tính.

## Milestone 1: Baseline

File gợi ý:

- `src/multi_agent_research_lab/cli.py`
- `src/multi_agent_research_lab/services/llm_client.py`

Baseline đã được thay bằng một search step + một LLM call duy nhất để agent tự research, phân tích và viết trong một context.

## Milestone 2: Supervisor

File gợi ý:

- `src/multi_agent_research_lab/agents/supervisor.py`
- `src/multi_agent_research_lab/graph/workflow.py`

Routing policy hiện dựa trên shared state: thiếu evidence → Researcher, thiếu analysis → Analyst, thiếu answer → Writer, đủ dữ liệu → `done`. `max_iterations` là guardrail bắt buộc.

Gợi ý câu hỏi thiết kế:

- Khi nào gọi Researcher?
- Khi nào gọi Analyst?
- Khi nào gọi Writer?
- Khi nào stop?
- Nếu agent fail thì retry hay fallback?

## Milestone 3: Worker agents

File gợi ý:

- `src/multi_agent_research_lab/agents/researcher.py`
- `src/multi_agent_research_lab/agents/analyst.py`
- `src/multi_agent_research_lab/agents/writer.py`

Mỗi worker chỉ chịu một responsibility và ghi output vào shared state để bước sau có thể kiểm tra/debug.

## Milestone 4: Trace và benchmark

File gợi ý:

- `src/multi_agent_research_lab/observability/tracing.py`
- `src/multi_agent_research_lab/evaluation/benchmark.py`
- `src/multi_agent_research_lab/evaluation/report.py`

Benchmark tối thiểu:

| Metric | Cách đo gợi ý |
|---|---|
| Latency | wall-clock time |
| Cost | token usage hoặc provider usage |
| Quality | rubric 0-10 do peer review |
| Citation coverage | số claims có source / tổng claims chính |
| Failure rate | số query fail / tổng query |

Chạy `make benchmark` để chạy cùng bộ query trong `configs/lab_default.yaml` qua cả hai pipeline và ghi `reports/benchmark_report.md`.

## Troubleshooting

### macOS: lỗi SSL certificate khi gọi API qua HTTPS (Tavily, OpenAI, ...)

Triệu chứng: khi implement `SearchClient` (hoặc bất kỳ HTTPS call nào) trên macOS, bạn có thể gặp lỗi kiểu:

```text
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
unable to get local issuer certificate
```

Nguyên nhân: Python cài từ python.org trên macOS **không dùng** certificate store của hệ điều hành, nên không tìm thấy CA bundle hợp lệ. Đây là lỗi môi trường, **không phải** do API key sai.

Cách khắc phục (chọn 1 trong 3):

1. **Chạy script cài certificate đi kèm Python** (nhanh nhất):

   ```bash
   /Applications/Python\ 3.12/Install\ Certificates.command
   ```

   (thay `3.12` bằng version Python của bạn)

2. **Dùng `certifi` trong code** — thêm `certifi` vào dependencies, rồi tạo SSL context khi gọi HTTPS.

3. **Set biến môi trường** trỏ tới CA bundle của certifi:

   ```bash
   export SSL_CERT_FILE=$(python -m certifi)
   ```

## Exit ticket

### 1. Case nào nên dùng multi-agent? Vì sao?

Nên dùng multi-agent khi bài toán có nhiều bước khác bản chất và mỗi bước có thể có contract riêng, ví dụ research cần tìm nguồn → đánh giá bằng chứng → tổng hợp câu trả lời có citation. Việc tách Researcher, Analyst và Writer giúp giảm overlap trách nhiệm, làm shared state và trace rõ hơn, cho phép kiểm tra từng failure mode, thay đổi từng agent độc lập, và thêm guardrail theo từng bước. Multi-agent đáng dùng khi lợi ích về grounding, khả năng debug và chất lượng đầu ra lớn hơn overhead latency/token.

### 2. Case nào không nên dùng multi-agent? Vì sao?

Không nên dùng multi-agent cho task ngắn, tuyến tính, một model call đã giải quyết tốt hoặc khi latency/cost là ưu tiên chính. Thêm Supervisor và nhiều handoff trong trường hợp này chỉ làm tăng số lần gọi model, tăng token/context chuyển tiếp và tạo thêm điểm lỗi mà không mang lại specialization thực sự. Với các query đơn giản, single-agent baseline thường dễ vận hành, nhanh và rẻ hơn.
