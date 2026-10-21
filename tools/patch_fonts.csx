using System;
using System.IO;
using System.Linq;
using UndertaleModLib;
using UndertaleModLib.Models;
using UndertaleModLib.Util;
using Newtonsoft.Json.Linq;

EnsureDataLoaded();
if (!Data.GeneralInfo.Name.Content.Equals("VernalEdge"))
    throw new Exception("Wrong game");
string folder = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(FilePath), "../../private/build/fonts"));
foreach (string filename in Directory.GetFiles(folder, "*.json"))
{
    JObject spec = JObject.Parse(File.ReadAllText(filename));
    string name = (string)spec["name"];
    var font = Data.Fonts.ByName(name);
    if (font == null) throw new Exception("Missing original font " + name);
    var oldPage = font.Texture.TexturePage;
    var page = new UndertaleEmbeddedTexture();
    page.Name = new UndertaleString("Korean " + name);
    page.TextureData.Image = GMImage.FromPng(File.ReadAllBytes(Path.ChangeExtension(filename, ".png")));
    Data.EmbeddedTextures.Add(page);
    ushort width = (ushort)(int)spec["width"], height = (ushort)(int)spec["height"];
    var item = new UndertaleTexturePageItem {
        Name = new UndertaleString("Korean " + name), TexturePage = page,
        SourceX=0, SourceY=0, SourceWidth=width, SourceHeight=height,
        TargetX=0, TargetY=0, TargetWidth=width, TargetHeight=height,
        BoundingWidth=width, BoundingHeight=height
    };
    Data.TexturePageItems.Add(item);
    font.Texture = item;
    var glyphs = font.Glyphs.ToDictionary(g => (int)g.Character);
    foreach (JObject g in spec["glyphs"])
    {
        int cp = (int)g["character"];
        glyphs[cp] = new UndertaleFont.Glyph {
            Character=(ushort)cp, SourceX=(ushort)(int)g["x"], SourceY=(ushort)(int)g["y"],
            SourceWidth=(ushort)(int)g["w"], SourceHeight=(ushort)(int)g["h"],
            Shift=(short)(int)g["shift"], Offset=(short)(int)g["offset"]
        };
    }
    font.Glyphs.Clear();
    foreach (var pair in glyphs.OrderBy(g => g.Key)) font.Glyphs.Add(pair.Value);
    font.RangeStart = font.Glyphs.First().Character;
    font.RangeEnd = font.Glyphs.Last().Character;
    if (Data.TextureGroupInfo != null)
    {
        foreach (var group in Data.TextureGroupInfo)
        {
            if (group.Fonts.Any(f => f.Resource == font) || group.TexturePages.Any(p => p.Resource == oldPage))
                group.TexturePages.Add(new UndertaleResourceById<UndertaleEmbeddedTexture, UndertaleChunkTXTR> { Resource=page });
        }
    }
    ScriptMessage(name + ": " + font.Glyphs.Count + " glyphs (original ID retained)");
}
