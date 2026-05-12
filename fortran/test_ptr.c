#include <stdio.h>
#include <stdint.h>
extern void write_42(int32_t* ptr);
int main() {
    int32_t val = 0;
    printf("Before: %d\n", val);
    write_42(&val);
    printf("After:  %d (expect 42)\n", val);
    return 0;
}
