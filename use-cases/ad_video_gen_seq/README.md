# E-commerce Marketing Video Generation

## Overview

> This project uses VeADK SequentialAgent (serial multi-agent orchestration) to generate e-commerce marketing videos. It builds a stable workflow by chaining “marketing planning / storyboard script / image generation / quality evaluation / video generation / final composition & publishing”. It’s suitable for quickly producing short product showcase videos (e.g., single-product promos, campaign materials).
>
> The example exposes a single Root Agent as the service entry point. Internally, multiple sub-agents execute in a fixed order, which is convenient for local debugging and cloud deployment.

- This project is derived from `04_ad_video_gen_a2a`, adapted for BytePlus AgentKit Runtime deployment.
- This project uses sequential-agent, while the multimedia example uses A2A for agent interaction.
- This project can be deployed on the AgentKit platform.

## Key Features

This project provides the following capabilities:

- **Marketing planning & generation configuration**: based on user input (product name / selling points / asset links), generates the video structure and generation parameters
- **Storyboard script generation**: automatically outputs shot scripts, including visual description, actions, and generation highlights
- **Text-to-image / image-to-image batch generation**: generates multiple candidate first-frame images per shot, with optional reference images
- **Image/video quality evaluation & selection**: scores candidate images/videos and selects the best to reduce trial-and-error cost
- **Text-to-video / first-frame guided video generation**: generates multiple video candidates per shot based on the selected first frame
- **Local composition & TOS upload**: stitches shot videos into a final video locally, then uploads to TOS and returns an accessible URL

## Agent Capabilities

The system exposes one Root Agent and orchestrates the following sub-agents in sequence:

- **Marketing Planning Agent (`market_agent`)**: parses user inputs, fills missing key info, and generates video configuration and shot count requirements
- **Storyboard Agent (`storyboard_agent`)**: produces shot scripts based on the configuration
- **Image Agent (`image_agent`)**: batch-generates candidate first-frame images for each shot
- **Image Evaluation Agent (`image_evaluate_agent`)**: scores and selects the best image per shot
- **Video Agent (`video_agent`)**: generates shot videos from selected images (supports batch generation and multiple candidates)
- **Video Evaluation Agent (`video_evaluate_agent`)**: evaluates and selects the best shot videos
- **Release Agent (`release_agent`)**: stitches selected shot videos into a final output and uploads to TOS, returning a link

### Cost Notes

| Related Service | Description |
| --- | --- |
| BytePlus ModelArk text model | Understands user inputs, plans the marketing story, and drives tool calls. |
| BytePlus ModelArk image model | Generates candidate first-frame images from text or reference images. |
| BytePlus ModelArk video model | Generates short video candidates from prompts and selected first frames. |
| BytePlus TOS | Stores uploaded user images and final merged videos. |

## Run Locally

### Prerequisites

Before starting, make sure your environment meets these requirements:

- Python 3.12 or later
- veadk-python 0.5.20 (see `pyproject.toml`)
- `uv` is recommended for dependency management
- `ffmpeg` available locally (used by `moviepy` for video composition)
- BytePlus ModelArk API key and model IDs
- BytePlus AK/SK with TOS permissions
- A pre-created BytePlus TOS bucket in `ap-southeast-1`

### Quick Start

Follow these steps to set up and run the project locally.

#### 1. Clone and install dependencies

```bash
# Clone the repository
git clone https://github.com/volcengine/agentkit-samples.git
cd agentkit-samples/python/02-use-cases/ad_video_gen_seq

# Install dependencies
uv sync --native-tls

# mac or linux
source .venv/bin/activate
# windows powershell
.venv\Scripts\activate
```

#### 2. Configure environment variables

Create `config.yaml` from `config.yaml.example`, then adapt it to BytePlus. The original example is Volcengine-oriented; for BytePlus, use the flatter `model.image` and `model.video` sections shown below. Keep non-secret config in `config.yaml` and keep secrets in `.env` or your deployment secret manager.

```bash
# Copy the config file
cp config.yaml.example config.yaml
```

Recommended BytePlus config shape:

```yaml
model:
  agent:
    name: <your_text_model_id>
    api_base: https://ark.ap-southeast.bytepluses.com/api/v3/
  image:
    name: <your_image_model_id>
    api_base: https://ark.ap-southeast.bytepluses.com/api/v3/
  video:
    name: <your_video_model_id>
    api_base: https://ark.ap-southeast.bytepluses.com/api/v3/
  evaluate:
    name: <your_eval_model_id>

byteplus:
  region: ap-southeast-1

database:
  tos:
    bucket: <your_existing_tos_bucket>
    region: ap-southeast-1
```

Create a local `.env` file for secrets and runtime flags:

```bash
BYTEPLUS_ACCESS_KEY=<your_byteplus_ak>
BYTEPLUS_SECRET_KEY=<your_byteplus_sk>
BYTEPLUS_REGION=ap-southeast-1

MODEL_AGENT_API_KEY=<your_modelark_api_key>
MODEL_IMAGE_API_KEY=<your_modelark_api_key>
MODEL_VIDEO_API_KEY=<your_modelark_api_key>

TOS_ENDPOINT=tos-ap-southeast-1.bytepluses.com
ENABLE_WEB_SEARCH=false
DISABLE_OPENAPI=true
```

Notes:

- `database.tos.bucket` must already exist; this sample does not create buckets automatically.
- `BYTEPLUS_ACCESS_KEY` / `BYTEPLUS_SECRET_KEY` are used for TOS upload.
- `MODEL_*_API_KEY` values are used by the text, image, video, and evaluation model calls.
- `ENABLE_WEB_SEARCH=false` is recommended for BytePlus because the original VeADK web-search tool targets a Volcengine-only service.
- `DISABLE_OPENAPI=true` disables `/docs`, `/redoc`, and `/openapi.json` in the served FastAPI app.

#### 3. Local debugging

- For local debugging, run `debug.py` to execute the workflow directly.

  ```bash
  uv run python debug.py
  ```

- Or debug via `veadk web`
  
  Use `veadk web` for local testing:

  ```bash
  uv run veadk web
  ```

By default it listens on `http://0.0.0.0:8000`.

You can also run the AgentKit server app locally:

```bash
uv run python main.py
```

`main.py` honors `PORT`, defaulting to `8000`.

#### 4. Product image inputs

You may include one product image URL in the first prompt. For example:

```text
Product image: https://your-bucket.tos-ap-southeast-1.bytepluses.com/product.jpeg
```

By default, image URLs are kept as text references for the planning agent because many text/planning models do not support image input. The downstream image tool can still use valid reference URLs. If the reference URL is malformed or unreachable, the image tool falls back to text-to-image instead of failing the whole workflow.

If you switch `MODEL_AGENT_NAME` to a vision-capable model and want the planning agent to receive image input directly, set:

```bash
ENABLE_AGENT_IMAGE_INPUT=true
```

#### 5. Debugging tips

Recommended way to quickly debug the full pipeline locally:

```bash
uv run python debug.py
```

## AgentKit Deployment

Configure BytePlus AgentKit credentials. You can use global config:

```bash
agentkit config --global --set byteplus.access_key=<your_byteplus_ak>
agentkit config --global --set byteplus.secret_key=<your_byteplus_sk>
```

Or use environment variables:

```bash
export BYTEPLUS_ACCESS_KEY=<your_byteplus_ak>
export BYTEPLUS_SECRET_KEY=<your_byteplus_sk>
```

Configure and deploy the runtime:

```bash
agentkit config \
    --cloud_provider byteplus \
    --region ap-southeast-1 \
    --agent_name ad_video_gen_seq \
    --entry_point main.py \
    --launch_type cloud \
    --image_tag v1.0.0

agentkit launch
```

If your environment does not package `.env`, configure the same secrets/runtime variables through AgentKit Runtime environment variables or secrets. Avoid putting secrets directly in shell history for production deployments.

To update an already configured deployment after code changes, run:

```bash
agentkit launch
```

### Technical Details

At its core, this project is a serial multi-agent workflow built with VeADK. The Root Agent orchestrates sub-agents in a fixed sequence to form a stable, reproducible video production pipeline:

User input → Marketing planning → Storyboard generation → Image generation → Image evaluation → Video generation → Video evaluation → Composition & upload

BytePlus adaptation notes:

- The service entrypoint is `main.py`, which serves one `root_agent`.
- All sub-agents run inside the same AgentKit runtime process.
- The final release step uses `video_combine_and_upload`, a deterministic tool that merges videos and uploads the final MP4 to TOS in one tool call.
- MoviePy video encoding is offloaded to a worker thread to avoid blocking AgentKit health checks.
- Generated media URLs are shortened internally as `⌥xxxxx` codes to reduce prompt size; tools resolve those codes before calling model or download APIs.

## Directory Structure

```plaintext
/
├── README.md                 # Chinese documentation
├── README_en.md              # English documentation
├── app/                      # Agents and tool implementations
│   ├── root/                 # Root orchestration entry (SequentialAgent)
│   ├── market/               # Marketing planning (video config / shot count, etc.)
│   ├── storyboard/           # Storyboard script generation
│   ├── image/                # Image generation and result structuring
│   ├── eval/                 # Image/video evaluation and selection
│   ├── video/                # Video generation (supports batch)
│   ├── release/              # Video stitching and upload
│   └── utils.py              # URL-code mapping, TOS upload, shared utilities
├── config.yaml.example       # Example config; adapt values to BytePlus
├── config.yaml               # Local model/TOS config, not necessarily committed
├── .env                      # Local secrets/runtime flags, do not commit
├── debug.py                  # Local debug script (does not start server)
├── model.py                  # Agent Model
├── main.py                   # Local service entry (AgentkitAgentServerApp)
├── pyproject.toml            # Dependency management (uv)
└── requirements.txt          # Dependency management (pip/uv pip)
```

## Example Prompts

Here are some commonly used prompt examples:

- `Please generate a short e-commerce marketing video for premium Arabica coffee beans. Product name: Mountain Dawn Arabica Coffee. Target audience: office workers and coffee lovers. Selling points: rich aroma, smooth taste, freshly roasted, suitable for morning focus and afternoon refreshment. Video style: warm, premium, natural lifestyle. Aspect ratio: 16:9.`
- `Please generate a short e-commerce marketing video for a women’s fashion brand. Product name: Aurora Linen Summer Dress. Target audience: young professional women and style-conscious shoppers aged 25-40. Selling points: breathable premium linen blend, elegant waistline, flattering A-line silhouette, soft pastel colors, suitable for brunch, vacation, and casual office wear. Video style: bright, elegant, feminine, premium lifestyle. Visual mood: warm natural sunlight, clean boutique setting, soft flowing fabric, confident modern woman. Aspect ratio: 16:9.`
- `Please generate a short e-commerce marketing video for handmade chicken pies. Product name: Golden Crust Chicken Pie. Product image: https://your-bucket.tos-ap-southeast-1.bytepluses.com/chicken-pie.jpeg Target audience: busy families, office workers, and people looking for convenient premium comfort food. Selling points: flaky golden pastry, creamy chicken filling, real chicken pieces, freshly baked taste, convenient for lunch or dinner. Video style: warm, appetizing, premium homemade bakery style. Visual mood: golden pastry close-ups, steam rising from a freshly cut pie, cozy kitchen lighting, comforting family meal moment. Aspect ratio: 16:9.`
- `Please generate a Christmas marketing video for chocolate. Product name: Christmas limited dark chocolate gift box. Applicable scenarios and audience: suitable for all chocolate lovers, especially consumers seeking the ultimate Christmas taste, sweet sharing, and energy replenishment; suitable for Christmas afternoon tea, holiday gatherings with friends and family, warm gift-giving, or any moment that needs a festive atmosphere. Main ingredients: selected cocoa beans, pure cocoa butter, premium milk, natural vanilla, no artificial colorants or preservatives, rich in antioxidants. Flavor/features: melts in the mouth, silky and rich, intense cocoa aroma, slightly bitter with a sweet aftertaste and a warm holiday-limited finish http://lf3-static.bytednsdoc.com/obj/eden-cn/lm_sth/ljhwZthlaukjlkulzlp/ark/assistant/images/ad_chocolate.png`
- `Please generate a bread marketing video. Product name: milky soft pull-apart toast. Scenarios/audience: scenarios: breakfast pairing, afternoon tea snacks, daily meal replacement; audience: office workers, students, families (bread lovers who prefer soft texture). Main ingredients: high-gluten flour, milk, eggs, butter, yeast, sugar. Flavor/features: rich milky aroma; tastes sweet and smooth when paired with butter + honey; features: soft crumb with even honeycomb pores, toasted crust with slightly charred spots, combining a soft interior and a crispy crust http://lf3-static.bytednsdoc.com/obj/eden-cn/lm_sth/ljhwZthlaukjlkulzlp/ark/assistant/images/ad_bread.jpeg`
- `Generate an e-commerce marketing video from product images for a wabi-sabi style scented candle. Product name: wabi-sabi scented candle. Scenarios/audience: scenarios: living room decor, bedroom sleep aid, study relaxation, minimalist ambience; audience: home decor lovers who like minimalism / wabi-sabi aesthetics, urban professionals seeking a relaxed vibe, fragrance collectors. Main ingredients: natural soy wax, essential oils, cement jar, paper label sticker. Scents/features: wood scents (cedar/sandalwood) or herbal scents (sage/eucalyptus), etc.; features: cement jar with raw texture, black-and-white minimalist patterned label; soft candlelight; jar reusable; overall understated and rustic, matching wabi-sabi aesthetics http://lf3-static.bytednsdoc.com/obj/eden-cn/lm_sth/ljhwZthlaukjlkulzlp/ark/assistant/images/ad_candle.jpeg`

## Demo Output

The system can:

- ✅ Automatically parse product information and generate marketing strategy
- ✅ Create high-quality video scripts and storyboards
- ✅ Generate engaging marketing copy
- ✅ Produce professional e-commerce marketing videos
- ✅ Provide video quality evaluation and optimization
- ✅ Support one-click publishing to multiple platforms

## FAQ

### Why is `web_search` disabled by default?

The original sample used VeADK's built-in web-search tool, which depends on a Volcengine service and Volcengine-style credentials. BytePlus users can generate videos without it by providing product details directly in the prompt.

### Can I pass product images?

Yes. Use one accessible HTTPS image URL in the first prompt. The planning model receives it as a text reference by default, and the image-generation tool validates it before use. If the URL is invalid, generation falls back to text-to-image.

### Why must the TOS bucket already exist?

The upload helper writes objects to an existing bucket and returns a signed URL. It does not create buckets.

### Why does local/cloud merging need `ffmpeg`?

The release step uses MoviePy to merge generated shot videos into a final MP4. MoviePy requires ffmpeg/libx264/aac support.

## License

This project is open-sourced. See the LICENSE file in the repository root for details.
