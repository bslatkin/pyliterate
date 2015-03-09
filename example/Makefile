OUTPUT_DIR = ./output
ALL_INPUTS = $(shell find . -name '*.md')

.PHONY: all build_dir
.DEFAULT_GOAL := all

$(OUTPUT_DIR)/%.md: %.md
	mkdir -p `dirname $@`
	cp $< $@
	run_markdown --overwrite $@
	- diff -C 3 $< $@

$(OUTPUT_DIR)/%.md:
	cat $^ > $@

$(OUTPUT_DIR)/Chapter1.md: \
		$(OUTPUT_DIR)/Chapter1/Introduction.md \
		$(OUTPUT_DIR)/Chapter1/Onion_rings.md \
		$(OUTPUT_DIR)/Chapter1/Falafel_balls.md

$(OUTPUT_DIR)/Chapter2.md: \
		$(OUTPUT_DIR)/Chapter2/Introduction.md \
		$(OUTPUT_DIR)/Chapter2/Salmon_fillet.md \
		$(OUTPUT_DIR)/Chapter2/Swordfish_steaks.md

$(OUTPUT_DIR)/Book_draft.md: \
		$(OUTPUT_DIR)/Chapter1.md \
		$(OUTPUT_DIR)/Chapter2.md

run:
	run_markdown \
		--overwrite \
		$(ALL_INPUTS)

crossreferences:
	cross_reference \
		--overwrite \
		$(ALL_INPUTS)

clean:
	rm -Rf $(OUTPUT_DIR)
