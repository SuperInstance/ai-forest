#include <stdio.h>
#include <stdint.h>

extern void set_val(int32_t val);
extern int32_t get_val(void);

int main() {
    set_val(42);
    printf("get_val = %d (expect 42)\n", get_val());
    return 0;
}
