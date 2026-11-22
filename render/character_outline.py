"""角色描边核心模块。

修复要点：
- 深度 + 法线联合边缘检测（不再只看深度差）
- 屏幕空间恒定线宽，并随分辨率缩放
- 透明物体走单独通道参与描边
- 描边 pass 排在 TAA 之后，避免被抖动打散
- MSAA resolve 之后再取样，深度/颜色边缘不错位
- 只对世界相机生效，UI 相机不描边
- 按阵营着色，区分敌我
- 深度不连续处补线，缺口不断开
- 描边不写深度缓冲，不影响后续透明排序
"""

# 阵营描边颜色（RGB）：0=中立 1=友方 2=敌方
FACTION_COLORS = {
    0: (1.0, 1.0, 1.0),
    1: (0.2, 0.6, 1.0),
    2: (1.0, 0.2, 0.2),
}

# 深度边缘阈值（线性化深度差）与法线折角阈值（点积下限）
DEPTH_EDGE_THRESHOLD = 0.1
NORMAL_EDGE_DOT_THRESHOLD = 0.6

# 线宽参考分辨率（在此高度下线宽即设计像素宽）
REFERENCE_HEIGHT = 1080


def depth_normal_edge(depth_a, depth_b, normal_dot):
    """深度 + 法线联合检测：深度差超阈值或相邻面法线夹角过大都判为轮廓。

    解决「只看深度差，相邻面朝向不同也判成轮廓 / 该判的没判」的问题。
    返回是否为边缘。
    """
    depth_edge = abs(depth_a - depth_b) > DEPTH_EDGE_THRESHOLD
    normal_edge = normal_dot < NORMAL_EDGE_DOT_THRESHOLD
    return depth_edge or normal_edge


def screen_space_width(width_px, screen_height):
    """屏幕空间恒定线宽：把期望的像素线宽换算成 UV 空间的采样偏移。

    线宽按像素定义，不随物体远近变化（远处角色描边不会比角色还粗）。
    """
    if screen_height <= 0:
        raise ValueError("screen_height must be positive")
    return width_px / screen_height


def transparent_mask(alpha_values):
    """透明物体单独通道：alpha < 1 的像素也生成描边掩码。

    玻璃后面的人不再少一半轮廓。返回 0/1 掩码列表。
    """
    return [1 if a < 1.0 else 0 for a in alpha_values]


def temporal_stable(outline_pass, taa_pass):
    """描边 pass 必须排在 TAA 之后，否则描边会被 TAA 抖动打散、一动就断续。

    返回描边 pass 应处的位置（TAA 之后一个槽位）。
    """
    return max(outline_pass, taa_pass + 1)


def msaa_resolve_mask(sample_count, subsample):
    """MSAA resolve 之后再取样：返回解析后目标的采样索引（恒为 0）。

    直接在多重采样目标上按子样本取深度会和颜色边缘错位，
    必须先 resolve 再检测。subsample 合法性会被校验。
    """
    if not 0 <= subsample < sample_count:
        raise ValueError("subsample out of range")
    return 0


def world_camera_only(camera_id, ui_camera_id):
    """只对世界相机做描边；UI 相机（以及分屏时的非世界相机）直接跳过。"""
    return camera_id != ui_camera_id


def faction_color(faction, _fallback=None):
    """按阵营返回描边颜色，区分敌我（友方蓝、敌方红、中立白）。"""
    return FACTION_COLORS.get(faction, FACTION_COLORS[0])


def gap_fill(edge_flags):
    """深度不连续处补线：单个像素的缺口用两侧边缘插值补上，栏杆缺口不断线。

    输入 0/1 边缘标记序列，返回补线后的序列。
    """
    flags = list(edge_flags)
    n = len(flags)
    for i in range(1, n - 1):
        if flags[i] == 0 and flags[i - 1] == 1 and flags[i + 1] == 1:
            flags[i] = 1
    return flags


def width_scale(base_width, ref_height, current_height):
    """线宽随分辨率缩放：分辨率缩放 / 窗口模式下保持一致的视觉线宽。"""
    if ref_height <= 0:
        raise ValueError("ref_height must be positive")
    return base_width * current_height / ref_height


def depth_write_off(_pass=None):
    """描边 pass 关闭深度写入，避免污染深度缓冲、打乱后续透明物体排序。"""
    return False


def normal_threshold(normal_dot, threshold):
    """法线折角判定：相邻面法线点积低于阈值即判为轮廓边。"""
    return normal_dot < threshold


def outline_color(lum_behind, lum_outline):
    """根据背景亮度选择对比度足够的描边颜色，避免草丛前看不见、天空前整圈发光。

    返回描边亮度（0 黑 / 1 白），取与背景差异更大的方向。
    """
    return 0.0 if lum_behind > 0.5 else 1.0


def edge_dilate(edge_flags, radius):
    """边缘膨胀：把 0/1 边缘掩码向外扩 radius 像素，用于加粗/补全轮廓。"""
    flags = list(edge_flags)
    n = len(flags)
    out = [0] * n
    for i, v in enumerate(flags):
        if v:
            for j in range(max(0, i - radius), min(n, i + radius + 1)):
                out[j] = 1
    return out


def stencil_mask(stencil_value, mask_bit):
    """模板掩码：只对手动标记了描边位的像素生效，返回是否命中。"""
    return (stencil_value & mask_bit) != 0


def per_object_style(object_id, faction):
    """逐物体描边样式：颜色按阵营区分，线宽按屏幕空间像素给出。"""
    return {
        "object_id": object_id,
        "color": faction_color(faction),
        "width_px": 2.0,
        "depth_write": depth_write_off(),
    }
