"""Render one Chatom message for every built-in backend."""

from chatom import MessageBuilder


def build_status_message():
    """Build a backend-independent status message."""
    return (
        MessageBuilder()
        .heading("Deployment status", level=2)
        .paragraph("The same message object is ready for every configured backend.")
        .bold("Environment: ")
        .text("production")
        .line_break()
        .bullet_list(["API: healthy", "Workers: healthy"])
        .table(
            [["API", "healthy"], ["Workers", "healthy"]],
            headers=["Service", "State"],
        )
        .build()
    )


def main():
    message = build_status_message()
    for backend in ("slack", "discord", "symphony", "telegram"):
        print(f"--- {backend} ---")
        print(message.render_for(backend))


if __name__ == "__main__":
    main()
