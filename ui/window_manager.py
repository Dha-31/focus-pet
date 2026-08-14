"""ui/window_manager.py：辅助窗口管理器（v3.7.1）。

- 同一时间只保留一个辅助窗口（商店/空间/成就/报表/设置/帮助/更换形象…）
- 打开新窗口时自动关闭旧的（避免层层叠叠 + 右键桌宠被模态窗口卡住）
- 辅助窗口不置顶、不抢焦点锁（只有桌宠本体置顶）
"""
_current = {"root": None}


def open(root):
    """注册一个辅助窗口；若已有其他辅助窗口，先自动关闭。"""
    close()
    if root is None:
        return
    _current["root"] = root
    try:
        root.bind("<Destroy>", _on_destroy, add="+")
    except Exception:
        pass


def close():
    if _current["root"] is not None:
        try:
            _current["root"].destroy()
        except Exception:
            pass
    _current["root"] = None


def current():
    return _current["root"]


def _on_destroy(event):
    if event.widget is _current["root"]:
        _current["root"] = None
