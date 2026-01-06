# ActionManifold
任務(Action)在事件與時間中所能展開的所有可能路徑的流形

---

## 🧩 ActionManifold — Description Layer & Development Layer 使用方式

### 1. 定義 StateMachine / Orchestrator 的 docstring

```python
class Login(StateMachine):
    """
    purpose: 處理登入
    inputs: username, password
    outputs: ok, error
    """
```

### 2. 定義 feature docstring（開發項目）

```python
async def input_password(self):
    """
    feature: 輸入密碼
    status: in_progress
    depends_on: Login.input_username
    """
```

### 3. 建立 Description Schema

```python
desc = DescriptionLayer(playbook)
schema = desc.build_schema()
```

### 4. 建立 Development Schema

```python
dev = DevelopmentLayer(playbook["registry"])
dev_items = dev.build_dev_items()
```

### 5. 契約檢查

```python
validator = ContractValidator(schema, playbook)
errors = validator.validate()
```

---

