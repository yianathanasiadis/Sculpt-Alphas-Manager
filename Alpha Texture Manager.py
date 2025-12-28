import bpy
import os
import bpy.utils.previews

bl_info = {
    "name": "Alpha Brush Manager",
    "version": (9, 0, 0),
    "blender": (5, 0, 0),
    "author": "Gemini AI",
    "description": "Auto-applies alphas with persistent root folder support.",
    "category": "Paint",
}

preview_collections = []

# --- 1. PREFERENCES (Saves the path permanently) ---
class AlphaManagerPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    main_directory: bpy.props.StringProperty(
        name="Global Alpha Root",
        subtype='DIR_PATH',
        description="Select the folder where all your alpha subfolders are located",
        default=""
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "main_directory")
        layout.label(text="Set this once to keep your library accessible across all projects.", icon='INFO')

# --- 2. LOGIC & DATA ---
def apply_alpha_logic(self, context):
    if self.image_gallery == "": return
    
    # Get path from Preferences instead of Scene
    addon_prefs = context.preferences.addons[__name__].preferences
    root = bpy.path.abspath(addon_prefs.main_directory)
    
    filepath = os.path.join(root, self.subfolder_enum, self.image_gallery)
    if not os.path.exists(filepath): return

    brush = getattr(context, "brush", None)
    if not brush and context.mode == 'SCULPT':
        brush = context.tool_settings.sculpt.brush
            
    if not brush or getattr(brush, "library", None): return 

    try:
        img = bpy.data.images.load(filepath, check_existing=True)
        if not brush.texture:
            brush.texture = bpy.data.textures.new(name="Alpha_Manager_Tex", type='IMAGE')
        brush.texture.image = img
    except: return

    if hasattr(brush, "texture_slot"):
        setattr(brush.texture_slot, "map_mode", 'VIEW_PLANE')
            
    setattr(brush, "stroke_method", 'ANCHORED')
    
    # Silent Falloff Firewall
    targets = [brush, getattr(brush, "falloff", None), getattr(brush, "falloff_curve", None)]
    for t in targets:
        if t and hasattr(t, "curve_preset"):
            try:
                setattr(t, "curve_preset", 'CONSTANT')
                break
            except: continue

    for area in context.screen.areas:
        if area.type == 'VIEW_3D': area.tag_redraw()

def get_image_previews(self, context):
    if not preview_collections: return []
    pcoll = preview_collections[0]
    
    addon_prefs = context.preferences.addons[__name__].preferences
    root = bpy.path.abspath(addon_prefs.main_directory)
    
    if not os.path.exists(root) or self.subfolder_enum in {"NONE", ""}: return []
    sub_dir = os.path.join(root, self.subfolder_enum)
    
    if sub_dir == pcoll.my_previews_dir and pcoll.my_previews_enum: return pcoll.my_previews_enum
    pcoll.clear()
    
    enum_items = []
    valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.tga', '.exr', '.hdr')
    if os.path.exists(sub_dir):
        files = sorted([f for f in os.listdir(sub_dir) if f.lower().endswith(valid_exts)])
        for i, name in enumerate(files):
            filepath = os.path.join(sub_dir, name)
            icon = pcoll.load(name, filepath, 'IMAGE')
            enum_items.append((name, name, filepath, icon.icon_id, i))
        pcoll.my_previews_dir = sub_dir
        pcoll.my_previews_enum = enum_items
    return enum_items

def get_subfolders(self, context):
    items = []
    addon_prefs = context.preferences.addons[__name__].preferences
    root = bpy.path.abspath(addon_prefs.main_directory)
    
    if root and os.path.exists(root):
        try:
            folders = sorted([f for f in os.listdir(root) if os.path.isdir(os.path.join(root, f))])
            for i, f in enumerate(folders):
                items.append((f, f, "", 'FILE_FOLDER', i))
        except: pass
    return items if items else [("NONE", "No folders found", "", 'ERROR', 0)]

# --- 3. UI & REGISTRATION ---
class BRUSH_OT_FixLockedBrush(bpy.types.Operator):
    bl_idname = "brush.fix_locked_alpha"
    bl_label = "Unlock Brush"
    def execute(self, context):
        bpy.ops.brush.asset_local_copy()
        return {'FINISHED'}

class AlphaProps(bpy.types.PropertyGroup):
    subfolder_enum: bpy.props.EnumProperty(name="Folder", items=get_subfolders)
    image_gallery: bpy.props.EnumProperty(name="", items=get_image_previews, update=apply_alpha_logic)

class VIEW3D_PT_AlphaManager(bpy.types.Panel):
    bl_label = "Alpha Brush Manager"
    bl_idname = "VIEW3D_PT_alpha_manager"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Alpha Manager"

    def draw(self, context):
        layout = self.layout
        props = context.scene.alpha_brush_props
        addon_prefs = context.preferences.addons[__name__].preferences
        
        brush = getattr(context, "brush", None)
        if not brush and context.mode == 'SCULPT':
            brush = context.tool_settings.sculpt.brush

        if brush and getattr(brush, "library", None):
            col = layout.column()
            col.alert = True
            col.operator("brush.fix_locked_alpha", icon='LOCKED', text="Unlock Selected Brush")
            layout.separator()

        if not addon_prefs.main_directory:
            layout.label(text="Please set Root in Addon Prefs", icon='ERROR')
            return

        layout.prop(props, "subfolder_enum")
        layout.separator()
        layout.template_icon_view(props, "image_gallery", show_labels=True)

def register():
    bpy.utils.register_class(AlphaManagerPreferences)
    bpy.utils.register_class(AlphaProps)
    bpy.utils.register_class(BRUSH_OT_FixLockedBrush)
    bpy.utils.register_class(VIEW3D_PT_AlphaManager)
    bpy.types.Scene.alpha_brush_props = bpy.props.PointerProperty(type=AlphaProps)
    pcoll = bpy.utils.previews.new()
    pcoll.my_previews_dir = ""
    pcoll.my_previews_enum = []
    preview_collections.append(pcoll)

def unregister():
    bpy.utils.unregister_class(AlphaManagerPreferences)
    bpy.utils.unregister_class(AlphaProps)
    bpy.utils.unregister_class(BRUSH_OT_FixLockedBrush)
    bpy.utils.unregister_class(VIEW3D_PT_AlphaManager)
    for pcoll in preview_collections: bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
    del bpy.types.Scene.alpha_brush_props

if __name__ == "__main__":
    register()