# PyPI 发布指南

本文档说明如何将 `llmagent` 包发布到 PyPI。

## 📋 发布前检查清单

### 1. 代码质量检查
- [ ] 所有测试通过：`pytest tests/test_api/ -v`
- [ ] 认证功能验证：健康检查端点免鉴权，业务端点支持 API Key 认证
- [ ] 打包验证：`python -m build` 成功，wheel 安装后 `import llm_agent` 正常
- [ ] 版本号确认：`src/llm_agent/__init__.py` 中的 `__version__` 正确

### 2. 元数据检查
- [ ] `pyproject.toml` 中的 `name = "llmagent"`
- [ ] `authors` 包含正确信息
- [ ] `project.urls` 指向正确的仓库地址
- [ ] `description` 和 `README.md` 内容准确
- [ ] `LICENSE` 文件存在（MIT）

### 3. 清理构建残留
```bash
rm -rf dist/ build/ *.egg-info/
```

---

## 🚀 发布步骤

### 准备工作

1. **安装发布工具**
```bash
pip install --upgrade build twine
```

2. **确认 PyPI 账号和 Token**
   - 访问 https://pypi.org/manage/account/token/
   - 创建 API Token，scope 选择 "Entire account" 或 "llmagent" 项目
   - 复制生成的 token（格式：`pypi-...`），首次发布后只显示一次

### 构建分发包

在 `llm_agent/` 目录下执行：

```bash
cd /path/to/autoAgent/llm_agent
python -m build
```

**预期输出**：
```
* Creating build/...
* Successfully built llmagent-0.1.0.tar.gz and llmagent-0.1.0-py3-none-any.whl
```

生成的文件在 `dist/` 目录：
- `llmagent-0.1.0.tar.gz` - 源码分发包
- `llmagent-0.1.0-py3-none-any.whl` - Wheel 二进制包

### 校验元数据

```bash
twine check dist/*
```

**预期输出**：
```
Checking dist/llmagent-0.1.0.tar.gz: PASSED
Checking dist/llmagent-0.1.0-py3-none-any.whl: PASSED
```

如果有 WARNING，检查 `pyproject.toml` 中的 `description` 是否过长或格式问题。

### （可选）TestPyPI 预演

首次发布建议先在 TestPyPI 验证流程：

```bash
# 上传到 TestPyPI
twine upload --repository testpypi dist/*

# 从 TestPyPI 安装测试
pip install -i https://test.pypi.org/simple/ llmagent

# 验证导入
python -c "import llm_agent; print('Version:', llm_agent.__version__)"

# 测试 CLI
llm-agent --version

# 测试 API 服务（如果有 [api] 依赖）
pip install -i https://test.pypi.org/simple/ 'llmagent[api]'
llm-agent server &
curl http://localhost:8000/api/v1/health
```

**TestPyPI 说明**：
- 测试环境，包不会永久保留
- 用于验证打包配置和安装流程
- 不影响正式 PyPI

### 正式发布到 PyPI

```bash
twine upload dist/*
```

**交互提示**：
```
Enter your username: __token__
Enter your password: pypi-xxxxxx...  # 粘贴你的 API Token
```

**预期输出**：
```
Uploading llmagent-0.1.0.tar.gz
100%|██████████████████████████████| 15k/15k [00:01<00:00, 11kNB/s]
Uploading llmagent-0.1.0-py3-none-any.whl
100%|██████████████████████████████| 20k/20k [00:01<00:00, 15kNB/s]

View at:
https://pypi.org/project/llmagent/
```

---

## ✅ 发布后验证

### 1. 从 PyPI 安装测试

```bash
# 在全新的虚拟环境中测试
python -m venv /tmp/test_venv
source /tmp/test_venv/bin/activate

# 从 PyPI 安装
pip install llmagent

# 验证导入
python -c "from llm_agent import LLMAgent, __version__; print('OK', __version__)"

# 测试 CLI
llm-agent --version

# 测试完整功能
pip install 'llmagent[all]'
llm-agent think "什么是递归？"
```

### 2. 验证 PyPI 页面

访问 https://pypi.org/project/llmagent/ 检查：
- 项目名称、版本号
- 描述信息是否正确
- README 是否正确渲染
- 作者信息
- 分类器（Classifiers）
- 依赖列表

### 3. 运行测试套件

```bash
pip install 'llmagent[dev]'
pytest tests/test_api/ -v
```

---

## 🔧 常见问题排查

### Q1: twine upload 报错 "HTTPError: 400 Bad Request"

**原因**：包名已被占用或元数据验证失败

**解决**：
1. 检查 `pyproject.toml` 中的 `name` 是否为 `llmagent`
2. 访问 https://pypi.org/project/llmagent/ 确认包名是否被占用
3. 如果被占用，需要更名（修改 `pyproject.toml` 的 `name` 字段）

### Q2: "HTTPError: 403 Forbidden"

**原因**：API Token 无效或 scope 不匹配

**解决**：
1. 确认 Token 复制完整（以 `pypi-` 开头）
2. 检查 Token scope 是否包含当前项目或 "Entire account"
3. 重新生成 Token

### Q3: README 在 PyPI 上渲染异常

**原因**：README.md 格式问题或缺少解析器

**解决**：
1. 确保 README.md 是标准 Markdown 格式
2. 如果使用 reStructuredText，需要在 `pyproject.toml` 配置：
   ```toml
   [project]
   readme = "README.md"
   # 或
   readme = "README.rst"
   content-type = "text/x-rst"
   ```

### Q4: wheel 安装后 import 失败

**原因**：src 布局配置错误或打包问题

**解决**：
1. 检查 `pyproject.toml` 中的 `[tool.setuptools.packages.find]` 配置：
   ```toml
   [tool.setuptools.packages.find]
   where = ["src"]
   include = ["llm_agent*"]
   ```
2. 重新构建：`python -m build`
3. 在干净 venv 测试安装

### Q5: 上传速度很慢或超时

**原因**：网络问题或 PyPI 服务器负载

**解决**：
1. 使用 `twine upload --skip-existing dist/*` 跳过已存在的文件
2. 检查网络连接
3. 稍后重试

---

## 📝 后续版本发布

### 1. 更新版本号

修改 `src/llm_agent/__init__.py`：
```python
__version__ = "0.2.0"  # 遵循语义化版本
```

### 2. 更新 CHANGELOG（推荐）

创建 `CHANGELOG.md` 记录变更：
```markdown
## [0.2.0] - 2025-01-XX

### Added
- 新功能描述

### Fixed
- 修复的问题

### Changed
- 破坏性变更说明
```

### 3. 重复发布步骤

```bash
# 清理旧构建
rm -rf dist/ build/

# 构建
python -m build

# 校验
twine check dist/*

# 发布
twine upload dist/*
```

---

## 🎯 最佳实践

1. **版本管理**：遵循语义化版本（Semantic Versioning）
   - `MAJOR.MINOR.PATCH`（如 0.1.0）
   - MAJOR：不兼容的 API 变更
   - MINOR：向后兼容的功能新增
   - PATCH：向后兼容的 Bug 修复

2. **预发布版本**：使用 alpha/beta/rc 标记
   ```toml
   version = "0.2.0a1"  # Alpha
   version = "0.2.0b1"  # Beta
   version = "0.2.0rc1" # Release Candidate
   ```

3. **Git Tag 对齐**：发布后在 git 打 tag
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

4. **保留 TestPyPI 测试习惯**：重大变更前先在 TestPyPI 验证

5. **自动化考虑**：可配置 GitHub Actions 自动发布（需 Trusted Publisher 配置）

---

## 📚 相关资源

- **PyPI 官方文档**：https://packaging.python.org/tutorials/packaging-projects/
- **Twine 使用指南**：https://twine.readthedocs.io/
- **语义化版本**：https://semver.org/
- **TestPyPI**：https://test.pypi.org/

---

**发布完成后，请更新本项目的 README.md 和文档中的版本号说明。**
