from app.templates.base import Formula, Template, select, text

SPEC = Template(
    title="Content Creator OS",
    icon="🎬",
    tagline="Turn a promising idea into a repeatable publishing process.",
    features=[
        "Organize ideas and production across multiple channels.",
        "Coordinate research, script, voice, visuals, editing and thumbnail preparation.",
        "Review views, likes, comments and subscribers gained after publication.",
    ],
    workflow=[
        "Choose a channel and audience problem; capture a clear hook in Ideas.",
        "Move the video through Idea → Research → Script → Voice → Visuals → Editing → Review → Scheduled → Published.",
        "Check the thumbnail, title and description, then publish manually on your platform.",
        "Log performance consistently and use the findings to improve the next idea.",
    ],
    manual=[
        "Create a Production Pipeline board grouped by Production Stage.",
        "Create channel-specific Publishing Calendar views using Publish Date.",
        "Create a monthly Performance view and count published videos to measure frequency.",
        "NTB Engagement Rate is (likes + comments) / views; format it as a percentage.",
        "Publishing and importing YouTube analytics require separate configuration; they are not automated.",
    ],
    properties={
        "Production Pipeline": {
            "Production Stage": select(
                "Idea",
                "Research",
                "Script",
                "Voice",
                "Visuals",
                "Editing",
                "Review",
                "Scheduled",
                "Published",
            ),
            "Thumbnail Status": select("Not Started", "In Progress", "Ready"),
            "Script Draft": text(),
            "Description Draft": text(),
            "Title Options": text(),
        }
    },
    formulas={
        "Performance": [
            Formula(
                "NTB Engagement Rate",
                'if(prop("Views") <= 0, 0, (prop("Likes") + prop("Comments")) / prop("Views"))',
                {"Views": "number", "Likes": "number", "Comments": "number"},
                True,
            )
        ]
    },
    prompts=[
        "Hooks: For [audience] facing [problem], write 10 truthful opening hooks for a video about [topic]. Avoid unsupported claims; label assumptions.",
        "Script: Draft a [duration] video about [topic] for [audience]. Include a hook, clear sections, visual cues and one next step. Mark factual claims that need verification.",
        "Titles: Suggest 12 specific, accurate titles for [video summary]. Explain the promise of each and avoid misleading clickbait.",
        "Description: Write a concise description for [video summary], with a clear opening, chapter placeholders and [approved links]. Do not invent links or timestamps.",
        "Ideas: Propose 15 video ideas for [channel niche] and [audience]. Include the audience question, angle, research needed and a simple success metric.",
    ],
)
