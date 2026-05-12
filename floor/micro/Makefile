CC       = gcc
CFLAGS   = -Wall -Wextra -O2 -std=c99
LDFLAGS  =
TARGET   = micro-agent
SRC      = micro.c

.PHONY: all clean run

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f $(TARGET)

run: $(TARGET)
	./$(TARGET) $(ARGS)
