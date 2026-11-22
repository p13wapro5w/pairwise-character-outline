# pairwise-character-outline

## 领域

游戏、图形与多媒体

## 主题

角色描边

## 说明

深度与法线联合检测、屏幕空间恒定线宽与透明物体处理。

初始状态下 `render/character_outline.py` 中所有函数抛出 `NotImplementedError`，测试全部失败。
修复实现后运行：

```bash
python -m pytest -q
```

期望全部通过。
