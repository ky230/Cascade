# Cascade Technical Whitepaper — Build Pipeline
# Usage: make pdf | make draft | make clean | make wordcount

PAPER_DIR  := $(dir $(MAKEFILE_LIST))..
BUILD_DIR  := $(dir $(MAKEFILE_LIST))
OUT_DIR    := $(BUILD_DIR)output
TEMPLATE   := $(BUILD_DIR)templates/arxiv-clean.tex
BIB        := $(BUILD_DIR)references.bib
METADATA   := $(PAPER_DIR)/00-metadata.yaml

SOURCES := $(PAPER_DIR)/01-introduction.md \
           $(PAPER_DIR)/02-related-work.md \
           $(PAPER_DIR)/03-architecture.md \
           $(PAPER_DIR)/04-agent-tools.md \
           $(PAPER_DIR)/05-proof-of-concept.md \
           $(PAPER_DIR)/06-evolution.md \
           $(PAPER_DIR)/07-conclusion.md

APPENDICES := $(PAPER_DIR)/appendix-changelog.md \
              $(PAPER_DIR)/appendix-traces.md \
              $(PAPER_DIR)/appendix-prompts.md

TARGET := $(OUT_DIR)/cascade-whitepaper.pdf
DRAFT  := $(OUT_DIR)/cascade-whitepaper-draft.pdf

PANDOC_BASE := pandoc \
    --from=markdown+smart+footnotes+pipe_tables+inline_code_attributes \
    --to=latex \
    --template=$(TEMPLATE) \
    --metadata-file=$(METADATA) \
    --bibliography=$(BIB) \
    --filter=pandoc-crossref \
    --citeproc \
    -M crossrefYaml=$(BUILD_DIR)filters/crossref-meta.yaml \
    --number-sections \
    --pdf-engine=latexmk \
    --pdf-engine-opt=-xelatex \
    --pdf-engine-opt=-interaction=nonstopmode \
    --resource-path=$(BUILD_DIR)figures

.PHONY: pdf draft clean clean-force wordcount check-deps clean-backup

pdf: check-deps $(TARGET)

$(TARGET): $(SOURCES) $(APPENDICES) $(METADATA) $(TEMPLATE) $(BIB)
	@mkdir -p $(OUT_DIR)
	$(PANDOC_BASE) $(SOURCES) $(APPENDICES) -o $@
	@echo "✅ PDF generated: $@"

draft: check-deps
	@mkdir -p $(OUT_DIR)
	$(PANDOC_BASE) -V draft=true \
	    -V watermark="DRAFT — $(shell date +%Y-%m-%d)" \
	    $(SOURCES) $(APPENDICES) -o $(DRAFT)
	@echo "📝 Draft PDF generated: $(DRAFT)"

wordcount:
	@cat $(SOURCES) | wc -w | xargs -I{} echo "Main body: {} words"
	@cat $(APPENDICES) | wc -w | xargs -I{} echo "Appendices: {} words"

clean:
	@echo "This will remove $(OUT_DIR)/, proceed? [y/N]"
	@read ans && [ "$$ans" = "y" ] && rm -rf $(OUT_DIR) || echo "Cancelled."

clean-force:
	rm -rf $(OUT_DIR)

clean-backup:
	rm -rf $(BUILD_DIR).pre_patch_backup

check-deps:
	@command -v pandoc >/dev/null 2>&1 || { echo "❌ pandoc not found. Install: brew install pandoc"; exit 1; }
	@command -v pandoc-crossref >/dev/null 2>&1 || { echo "❌ pandoc-crossref not found. Install: brew install pandoc-crossref"; exit 1; }
	@command -v latexmk >/dev/null 2>&1 || { echo "❌ latexmk not found. Install via MacTeX or texlive"; exit 1; }
