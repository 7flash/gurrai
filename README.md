# GurrAI 🧠🚀

Welcome to **GurrAI**, the most efficient prompting tool designed for unparalleled productivity in AI interactions. By leveraging the power of the Helix editor—the best way to write and read in a `vim`-like fashion—and the command line interface (CLI), GurrAI offers a seamless, iterative, and highly engaging experience for developers and AI enthusiasts alike.

---

### Table of Contents

1. [Setup](#setup)
2. [Usage](#usage)
    - [Basic Interaction](#basic-interaction)
    - [Unix-like Interaction](#unix-like-interaction)
    - [Referencing Files and Sections](#referencing-files-and-sections)
    - [Referencing Local and Global Paths](#referencing-local-and-global-paths)
    - [Roles and Ignoring Messages](#roles-and-ignoring-messages)
3. [Important Dependency](#important-dependency)
4. [Contributing](#contributing)
5. [License](#license)

---

### Setup 🛠️

Setting up GurrAI is straightforward and essential for a smooth experience. Follow these steps to get up and running:

1. **Clone the repository to your local machine:**
    ```bash
    git clone https://github.com/7flash/gurrai.git ~/Documents/gurrai
    ```

2. **Navigate to the project directory:**
    ```bash
    cd ~/Documents/gurrai
    ```

3. **Add an alias in your `.zshrc` file to expedite the invocation of GurrAI:**
    ```bash
    echo "alias ai='sh ~/Documents/gurrai/src/ai.sh gpt-4o'" >> ~/.zshrc
    source ~/.zshrc
    ```

Adding this alias ensures that you can quickly start prompting by simply typing `ai` in your terminal. This step is a crucial part of the setup.

---

### Usage 📚

GurrAI offers several versatile methods to interact with AI, enhancing both productivity and ease of use.

#### Basic Interaction 💬

To kickstart your conversation with AI, simply run `ai` in the terminal:

```bash
ai
```

- **Step 1:** Type your prompt in the Helix editor.
- **Step 2:** See the response in the Helix editor spawned along with your prompt.
- **Step 3:** Iteratively continue your conversation.

This workflow allows you to refine and build upon your prompts iteratively, making your AI interactions more productive and fluid.

#### Unix-like Interaction 🐚

GurrAI supports Unix-like interactions, allowing you to spawn a new conversation by piping a prompt file:

```bash
cat prompts/example.txt | ai
```

This command reads the content of `example.txt` and uses it as the prompt for the AI. It's a true Unix way of interacting with AI!

#### Referencing Files and Sections 📁

You can reference any local files directly within your prompt:

```markdown
file:./path/to/yourfile.txt
```

For more granular control, you can reference specific sections of files using hashtags after the file name:

```python
file:./path/to/yourfile.py#section
```

In Python files, GurrAI will look for comments such as `# .section` to locate the referenced section. For other file types, the corresponding comment style (e.g., `// .section` for JavaScript) will be used.

#### Referencing Local and Global Paths 🌐

You can reference local paths relative to the `prompts` folder, as well as global paths starting with `/`:

```markdown
file:./relative/path/to/file.txt
file:/absolute/path/to/file.txt
```

This flexibility ensures you can easily include any necessary files or sections in your prompts.

#### Roles and Ignoring Messages 🎭

GurrAI supports defining different message roles within your prompt file using the `|role|` separator between messages. For example:

```markdown
|user| What is the weather today?
|assistant| The weather is sunny with a high of 25°C.
```

You can also exclude messages by adding `!ignore` after the `|role|`:

```markdown
|user|
What is the weather today?
|assistant|!ignore
The weather is sunny with a high of 25°C.
```

This feature allows you to control which messages are processed and which are not, enhancing the flexibility of your interactions.

---

### Important Dependency 🍃

GurrAI relies on the Helix editor, which provides a powerful, efficient, and intuitive way to interact with your prompts and AI responses. The Helix editor's `vim`-like style makes it the best editor for this purpose.
