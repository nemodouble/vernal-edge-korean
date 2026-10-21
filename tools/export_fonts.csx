using System;
using System.IO;
using System.Linq;
using UndertaleModLib;
using UndertaleModLib.Util;
using Newtonsoft.Json;

EnsureDataLoaded();
string folder = Path.Combine(Path.GetDirectoryName(FilePath), "font-export");
Directory.CreateDirectory(folder);
using (var worker = new TextureWorker())
{
    foreach (var font in Data.Fonts)
    {
        worker.ExportAsPNG(font.Texture, Path.Combine(folder, font.Name.Content + ".png"));
        File.WriteAllText(Path.Combine(folder, font.Name.Content + ".json"), JsonConvert.SerializeObject(new {
            name = font.Name.Content, displayName = font.DisplayName.Content,
            emSize = font.EmSize, ascender = font.Ascender, ascenderOffset = font.AscenderOffset,
            glyphs = font.Glyphs.Select(g => new { character = g.Character, x=g.SourceX, y=g.SourceY,
                w=g.SourceWidth, h=g.SourceHeight, shift=g.Shift, offset=g.Offset })
        }, Formatting.Indented));
        ScriptMessage(font.Name.Content + ": " + font.Glyphs.Count + " glyphs");
    }
}
