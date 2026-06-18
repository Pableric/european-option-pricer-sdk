CC ?= gcc
CFLAGS ?= -O3 -march=native -Wall -Wextra -Iinclude

.PHONY: all example run check-private clean

all: example check-private

example: examples/basic

examples/basic: examples/basic.c include/european_pricer.h lib/libeuropean_pricer.so
	$(CC) $(CFLAGS) examples/basic.c -Llib -leuropean_pricer -Wl,-rpath,'$$ORIGIN/../lib' -lm -o $@

run: examples/basic
	./examples/basic

check-private:
	@python3 scripts/check_private.py

clean:
	rm -f examples/basic

