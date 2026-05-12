#include <stdio.h>
#include <stdint.h>
extern void double_arr(int32_t* arr, int n);
int main() {
    int32_t arr[5] = {1, 2, 3, 4, 5};
    printf("Before: %d %d %d %d %d\n", arr[0], arr[1], arr[2], arr[3], arr[4]);
    double_arr(arr, 5);
    printf("After:  %d %d %d %d %d\n", arr[0], arr[1], arr[2], arr[3], arr[4]);
    return 0;
}
