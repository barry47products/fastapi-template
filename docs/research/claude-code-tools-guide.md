# Claude Code Tools Guide

Quick reference guide for all available tools in Claude Code.

## 🔧 File Operations

### Read

View file contents including images, PDFs, and Jupyter notebooks.

- `file_path`: Absolute path to file
- `offset`: Line number to start reading from
- `limit`: Number of lines to read

### Write

Create new files or overwrite existing ones.

- `file_path`: Absolute path for new file
- `content`: File content to write

### Edit

Make targeted changes to existing files.

- `file_path`: File to modify
- `old_string`: Text to replace
- `new_string`: Replacement text
- `replace_all`: Replace all occurrences (default: false)

### MultiEdit

Make multiple edits to the same file in one operation.

- `file_path`: File to modify
- `edits`: Array of edit operations

### Glob

Fast file pattern matching across any codebase size.

- `pattern`: Glob pattern (`**/*.py`, `src/**/*.ts`)
- `path`: Directory to search (optional, defaults to current)

### LS

List files and directories.

- `path`: Absolute path to directory
- `ignore`: Array of glob patterns to exclude

## 🔍 Code Search & Analysis

### Grep

Powerful search tool built on ripgrep with full regex support.

- `pattern`: Regular expression pattern
- `path`: File or directory to search
- `output_mode`: "content", "files_with_matches", "count"
- `type`: File type filter (`py`, `js`, `rust`, etc.)
- `glob`: Glob pattern filter
- `-i`: Case insensitive search
- `-A/-B/-C`: Context lines after/before/around matches
- `-n`: Show line numbers
- `multiline`: Enable multiline pattern matching

## 🖥️ System & Development

### Bash

Execute shell commands with optional timeout and background execution.

- `command`: Command to execute
- `description`: Brief description of command purpose
- `timeout`: Timeout in milliseconds (max 600000)
- `run_in_background`: Run command in background

### BashOutput

Retrieve output from background bash processes.

- `bash_id`: ID of background shell
- `filter`: Optional regex to filter output lines

### KillBash

Terminate background bash processes.

- `shell_id`: ID of shell to kill

## 🤖 IDE Integration

### mcp**ide**getDiagnostics

Get language diagnostics from VS Code.

- `uri`: Optional file URI (gets all files if not specified)

### mcp**ide**executeCode

Execute Python code in Jupyter kernel.

- `code`: Python code to execute

## 🌐 Web & External

### WebSearch

Search the web for current information.

- `query`: Search query
- `allowed_domains`: Only include results from these domains
- `blocked_domains`: Exclude results from these domains

### WebFetch

Fetch and analyze web page content with AI processing.

- `url`: URL to fetch
- `prompt`: Analysis prompt for the content

## 🤖 Specialized Agents

### Task

Launch specialized agents for complex, multi-step work.

- `subagent_type`: Agent type to use
- `description`: Short task description
- `prompt`: Detailed task instructions

#### Available Agent Types

- **general-purpose**: Research, code search, multi-step tasks
- **statusline-setup**: Configure Claude Code status line
- **output-style-setup**: Create Claude Code output styles

## 📝 Project Management

### TodoWrite

Create and manage structured task lists.

- `todos`: Array of todo items with:
  - `content`: Task description (imperative form)
  - `activeForm`: Present continuous form for execution
  - `status`: "pending", "in_progress", "completed"

## 📓 Notebook Operations

### NotebookEdit

Edit Jupyter notebook cells.

- `notebook_path`: Absolute path to .ipynb file
- `cell_id`: ID of cell to edit
- `new_source`: New cell content
- `cell_type`: "code" or "markdown"
- `edit_mode`: "replace", "insert", "delete"

## 🚀 Development Workflow

### ExitPlanMode

Exit planning mode and proceed with implementation.

- `plan`: The implementation plan for user approval

## 🔧 Common Patterns

### Code Search

```bash
# Find all error handling
Grep: pattern="try.*except" type="py"

# Search specific files
Grep: pattern="TODO|FIXME" glob="src/**/*.py" output_mode="content"
```

### File Operations

```bash
# Find Python files
Glob: pattern="**/*.py"

# Multiple edits
MultiEdit: file_path="/path/to/file.py"
           edits=[{old_string: "old", new_string: "new"}]
```

### Background Tasks

```bash
# Run tests in background
Bash: command="poetry run pytest" run_in_background=true

# Monitor output
BashOutput: bash_id="<shell_id>"
```

### Complex Work

```bash
# Research task
Task: subagent_type="general-purpose"
      prompt="Research FastAPI async patterns for database integration"

# Track progress
TodoWrite: todos=[{content: "Implement feature", status: "pending",
                  activeForm: "Implementing feature"}]
```

## 💡 Best Practices

### When to Use Each Tool

- **Grep**: Code search, finding patterns, debugging
- **Task**: Complex research, multi-step implementations
- **MultiEdit**: Multiple changes to same file
- **Bash**: Running tests, builds, git operations
- **TodoWrite**: Complex feature development tracking
- **Read/Edit**: Simple file modifications
- **Glob**: Finding files by name patterns

### Performance Tips

- Use `type` parameter in Grep for faster searches
- Use `head_limit` to limit large result sets
- Run long commands with `run_in_background=true`
- Use MultiEdit for multiple changes to avoid repeated file I/O

### Development Workflow

1. Use **Grep** to understand existing code
2. Use **Task** for complex planning or research
3. Use **TodoWrite** to track implementation phases
4. Use **Read/Edit/MultiEdit** for implementation
5. Use **Bash** for testing and validation

---

**Note**: This guide provides quick reference information. Each tool has additional parameters and options - refer to the tool descriptions during usage for complete parameter lists.
