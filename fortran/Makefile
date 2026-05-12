CC = gfortran
CFLAGS = -O3 -fPIC -fopenmp -march=native -mtune=native
LDFLAGS = -shared -fopenmp -O3
LIB = libplato_math.so

all: $(LIB)

$(LIB): plato_math.f90
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^

bench:
	python3 bench_contract.py

.PHONY: all clean bench

clean:
	rm -f $(LIB) *.o *.so
