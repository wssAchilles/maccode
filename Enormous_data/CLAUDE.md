# Enormous Data - Model Usage Policy

## Model Selection Rules

### Default Model: Opus (mimo-v2.5 pro)

All daily code tasks MUST use **Opus (mimo-v2.5 pro)**, including but not limited to:

- Code writing, editing, and refactoring
- Bug fixing and debugging
- Code review
- Architecture design and planning
- Test writing and TDD workflows
- Documentation writing
- Git operations and PR creation
- Build error resolution
- Performance optimization
- LaTeX document editing and compilation

### Exception: Image Recognition Tasks

When a task involves **image recognition or visual analysis**, MUST switch to **mimo-v2.5 Custom Haiku model**. This applies to:

- Reading and analyzing screenshots
- Interpreting diagrams, charts, or visual layouts
- UI/UX visual review
- OCR or text extraction from images
- Any task requiring visual understanding of image content

### How to Switch Models

Use `/model` command to switch between models:
- `/model` then select `mimo-v2.5 pro` for code tasks
- `/model` then select `mimo-v2.5` (Custom Haiku) for image tasks

## Rationale

- **Opus (mimo-v2.5 pro)**: Best reasoning and code generation quality for engineering tasks
- **mimo-v2.5 Custom Haiku**: Specialized for visual understanding and image processing tasks
