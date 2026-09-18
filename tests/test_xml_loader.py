"""Test XML loading and legal-unit chunking."""

from rag_bogado.ingestion.xml_loader import (
    chunk_legal_units,
    load_xml,
    load_xml_chunks,
)

SAMPLE_XML = """This XML file does not appear to have any style information.
<documento fecha_actualizacion="20260724102601">
  <metadatos>
    <identificador>DOUE-L-2024-81079</identificador>
    <titulo>Reglamento de Inteligencia Artificial</titulo>
  </metadatos>
  <texto>
    <div>
      <table class="sinbordes">
        <tr>
          <td><p class="parrafo">(1)</p></td>
          <td><p class="parrafo">Objetivo: establecer normas.</p></td>
        </tr>
        <tr>
          <td><p class="parrafo">(2)</p></td>
          <td><p class="parrafo">Proteger los derechos y la salud.</p></td>
        </tr>
      </table>
      <p class="capitulo_num">CAPÍTULO I</p>
      <p class="capitulo_tit"><span>DISPOSICIONES GENERALES</span></p>
      <p class="articulo">Artículo 1</p>
      <p class="parrafo">Objeto</p>
      <p class="parrafo">1. Este Reglamento regula la IA.</p>
      <p class="articulo">Artículo 4</p>
      <p class="parrafo">Alfabetización en materia de IA</p>
      <p class="parrafo">Los proveedores adoptarán medidas para su personal.</p>
      <p class="anexo_num">ANEXO I</p>
      <p class="anexo_tit">Lista de actos</p>
      <p class="parrafo">Directiva 2000/1/CE.</p>
    </div>
  </texto>
</documento>
"""


def test_load_xml_extracts_recitals_articles_and_annexes(tmp_path):
    xml_file = tmp_path / "sample.xml"
    xml_file.write_text(SAMPLE_XML, encoding="utf-8")

    units = load_xml(xml_file)

    assert len(units) == 5
    assert [u.unit_type for u in units] == [
        "recital",
        "recital",
        "article",
        "article",
        "annex",
    ]

    art4 = [u for u in units if u.identifier == "Artículo 4"][0]
    assert art4.title == "Alfabetización en materia de IA"
    assert "Los proveedores adoptarán medidas" in art4.text
    assert art4.source == "sample.xml"

    rec1 = [u for u in units if u.identifier == "Considerando (1)"][0]
    assert "Objetivo: establecer normas." in rec1.text


def test_chunk_legal_units_preserves_prefix_and_metadata(tmp_path):
    xml_file = tmp_path / "sample.xml"
    xml_file.write_text(SAMPLE_XML, encoding="utf-8")

    chunks = load_xml_chunks(xml_file, max_chunk_size=500)

    assert len(chunks) == 5
    art4_chunk = [c for c in chunks if c.article == "Artículo 4"][0]
    assert art4_chunk.unit_type == "article"
    assert art4_chunk.page_number == 0
    assert "Artículo 4. Alfabetización en materia de IA" in art4_chunk.text
    assert "Los proveedores adoptarán medidas" in art4_chunk.text


def test_chunk_legal_units_splits_long_units(tmp_path):
    xml_file = tmp_path / "long.xml"
    long_paras = "\n".join(
        f'<p class="parrafo">Párrafo {i}: {"Texto explicativo largo " * 10}.</p>'
        for i in range(10)
    )
    long_xml = f"""<documento>
      <texto>
        <p class="articulo">Artículo 10</p>
        <p class="parrafo">Gobernanza de datos</p>
        {long_paras}
      </texto>
    </documento>"""
    xml_file.write_text(long_xml, encoding="utf-8")

    units = load_xml(xml_file)
    chunks = chunk_legal_units(units, max_chunk_size=300)

    assert len(chunks) > 1
    assert all(c.article == "Artículo 10" for c in chunks)
    assert all(c.unit_type == "article" for c in chunks)
    assert all("Artículo 10. Gobernanza de datos" in c.text for c in chunks)


def test_load_boe_xml_structure(tmp_path):
    boe_xml = """<?xml version="1.0" encoding="utf-8"?>
<response>
  <status>
    <code>200</code>
    <text>ok</text>
  </status>
  <data>
    <metadatos>
      <identificador>BOE-A-2018-16673</identificador>
      <titulo>Ley Orgánica de Protección de Datos</titulo>
    </metadatos>
    <texto>
      <p class="articulo">Artículo 1. Objeto de la ley.</p>
      <p class="parrafo">1. La presente ley orgánica tiene por objeto...</p>
      <p class="articulo">Artículo 2. Ámbito de aplicación.</p>
      <p class="parrafo">El régimen de protección de datos se aplicará a...</p>
    </texto>
  </data>
</response>"""
    xml_file = tmp_path / "boe.xml"
    xml_file.write_text(boe_xml, encoding="utf-8")

    units = load_xml(xml_file)
    assert len(units) == 2
    assert units[0].unit_type == "article"
    assert units[0].identifier == "Artículo 1"
    assert units[0].title == "Objeto de la ley."
    assert "La presente ley orgánica" in units[0].text
    assert units[1].identifier == "Artículo 2"
    assert units[1].title == "Ámbito de aplicación."

    chunks = chunk_legal_units(units, max_chunk_size=500)
    assert len(chunks) == 2
    assert chunks[0].article == "Artículo 1"
    assert "Artículo 1. Objeto de la ley" in chunks[0].text


def test_load_xml_ignores_analisis_texto_and_finds_main_texto(tmp_path):
    xml_with_analisis = """<?xml version="1.0" encoding="UTF-8"?>
<documento fecha_actualizacion="20260720122602">
  <metadatos>
    <identificador>BOE-A-2018-16673</identificador>
    <titulo>Ley Orgánica 3/2018</titulo>
  </metadatos>
  <analisis>
    <referencias>
      <anterior referencia="BOE-A-2018-10753">
        <palabra codigo="101">DEROGA</palabra>
        <texto>el Real Decreto-ley 5/2018, de 27 de julio</texto>
      </anterior>
    </referencias>
  </analisis>
  <texto>
    <p class="articulo">Artículo 1. Objeto de la ley.</p>
    <p class="parrafo">1. La presente ley tiene por objeto la protección de datos.</p>
    <p class="articulo">Artículo 2. Ámbito.</p>
    <p class="parrafo">El ámbito de aplicación incluye el tratamiento de datos.</p>
  </texto>
</documento>"""
    xml_file = tmp_path / "boe_with_analisis.xml"
    xml_file.write_text(xml_with_analisis, encoding="utf-8")

    units = load_xml(xml_file)
    assert len(units) == 2
    assert units[0].identifier == "Artículo 1"
    assert "protección de datos" in units[0].text
    assert units[1].identifier == "Artículo 2"
