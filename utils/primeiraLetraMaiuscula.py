def titlecase_pt(s: str) -> str:
  s = ("" if s is None else str(s)).strip().lower()
  if not s:
    return ""
  minusculas = {"da", "de", "do", "das", "dos", "e", "di", "du", "del", "van", "von", "d"}
  tokens = s.split()

  def cap_word(w: str) -> str:
    # trata hifens: "maria-joao" -> "Maria-Joao"
    parts = []
    for p in w.split("-"):
      if p == "":
        parts.append(p)
      else:
        # trata "d'ávila" -> "d'Ávila"
        if len(p) > 2 and p[:2] == "d'":
          parts.append("d'" + p[2:3].upper() + p[3:])
        else:
          parts.append(p[:1].upper() + p[1:])
    return "-".join(parts)

  out = []
  for i, w in enumerate(tokens):
    if i > 0 and w in minusculas:
      out.append(w)
    else:
      out.append(cap_word(w))
  return " ".join(out)