"""Generate a standalone .docx containing the updated MAX2-KO propagation paragraph."""
from docx import Document
from docx.shared import Pt

TEXT = (
    "The perturbation process is illustrated for the Arabidopsis shoot branching "
    "network (Figure 2A), where 38 nodes and 75 edges capture the interplay "
    "between core genetic regulators, hormonal signalling pathways, and "
    "environmental inputs. To demonstrate how these cascade networks generate "
    "predictions, we trace the propagation of a MAX2 gene knockout through the "
    "strigolactone signalling module (Figure 2B,C). Under control conditions, "
    "all nodes converge to a baseline value of 1 and the phenotype remains at "
    "steady state (Figure 2B). When MAX2 is knocked out by setting its modifier "
    "to 0, the loss of MAX2-mediated degradation causes its targets SMXL6/7/8 "
    "and BES1 to accumulate, which in turn suppresses BRC1 expression both "
    "directly and through repression of its co-activator SPL9. The collapse of "
    "BRC1 derepresses the auxin transporter PIN3 and abolishes the "
    "BRC1\u2192HB21\u2192NCED3\u2192ABA branch-inhibitory cascade, while "
    "SMXL6/7/8 simultaneously up-regulates PIN1; together, these rearrangements "
    "produce a predicted increase in shoot branching, correctly matching the "
    "experimentally observed increased branching phenotype of MAX2 mutants "
    "(Figure 2C,D). This example illustrates how the cascade architecture "
    "translates a single genetic perturbation into a directional phenotypic "
    "prediction through a chain of mechanistically interpretable regulatory "
    "steps."
)

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Times New Roman"
style.font.size = Pt(11)

para = doc.add_paragraph(TEXT)
para.paragraph_format.first_line_indent = Pt(0)

out = "max2_propagation_paragraph.docx"
doc.save(out)
print(f"wrote {out}")
