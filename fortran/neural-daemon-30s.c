#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

int plato_read_tiles(const char *room, int *buffer, int max_tiles);
int plato_write_tile(const char *room, const char *question, const char *answer,
                     const char *source, double confidence);

static unsigned long long rng = 42;
static int ri(int max) { rng = (rng * 6364136223846793005ULL + 1442695040888963407ULL) % 9223372036854775807ULL; return (int)(rng % (unsigned long long)max); }

static void permute(int *t, int n) { for (int i = n-1; i > 0; i--) { int j = ri(i+1); int tmp = t[i]; t[i] = t[j]; t[j] = tmp; } }
static void blend(int *t, int n, int mu) { for (int i = 0; i < n; i++) { int p = ri(n); t[i] += (int)((long long)(t[p]-t[i])*mu/1024); } }
static void perturb(int *t, int n, int m) { for (int i = 0; i < n; i++) t[i] += ri(m*2+1)-m; }

static int filter(int *t, int n, int th, int *out) {
    int no = 0;
    for (int i = 0; i < n; i++) {
        int d = 0;
        for (int j = i-3; j <= i+3 && j < n; j++)
            if (j >= 0 && j != i && abs(t[i]-t[j]) > th) d++;
        if (d >= 2) out[no++] = t[i];
    }
    return no;
}

static int cycle(int *t, int n, int sd, int mu, int mg, int th, int *out) {
    rng = sd; permute(t, n); blend(t, n, mu); perturb(t, n, mg);
    return filter(t, n, th, out);
}

int main(int argc, char **argv) {
    const char *room = argc > 1 ? argv[1] : "tension";
    int interval = argc > 2 ? atoi(argv[2]) : 30;
    int cycle_num = 0;
    printf("Neural PLATO Daemon (C)\n  Room: %s/\n  Interval: %ds\n\n", room, interval);
    
    while (1) {
        cycle_num++;
        int buf[1024], work[1024], out[1024];
        int n = plato_read_tiles(room, buf, 500);
        if (n == 0) { printf("[%d] No tiles\n", cycle_num); sleep(interval); continue; }
        memcpy(work, buf, n * sizeof(int));
        
        int nv = cycle(work, n, 42 + cycle_num, 512, 5000, 1000, out);
        if (nv > 200) nv = 200;
        
        int written = 0;
        for (int i = 0; i < nv && i < 20; i++) {
            char q[64], a[128];
            snprintf(q, sizeof(q), "neural %d c%d", i, cycle_num);
            snprintf(a, sizeof(a), "v=0x%08X seed_cycle output", out[i] & 0xFFFFFF);
            if (plato_write_tile("neural-inference", q, a, "c-daemon", 0.85))
                written++;
        }
        printf("[%d] %d tiles → %d variants → wrote %d\n", cycle_num, n, nv, written);
        fflush(stdout);
        sleep(interval);
    }
    return 0;
}
