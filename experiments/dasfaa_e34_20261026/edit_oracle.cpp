// Independent exhaustive CPU rolling-row edit oracle; top-10 per query.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <queue>
#include <stdexcept>
#include <string>
#include <vector>
#include <unistd.h>
#ifdef _OPENMP
#include <omp.h>
#endif

void require(bool ok, const char* why) { if (!ok) throw std::runtime_error(why); }
struct Strings {
    int n = 0, stride = 0;
    std::vector<int> len;
    std::vector<char> text;
    explicit Strings(const char* path) {
        std::ifstream f(path, std::ios::binary);
        f.read(reinterpret_cast<char*>(&n), 4);
        f.read(reinterpret_cast<char*>(&stride), 4);
        require(bool(f) && n > 0 && stride == 109, "invalid string header");
        f.seekg(0, std::ios::end);
        require(f.tellg() == std::streamoff(8 + int64_t(n) * (4 + stride)), "truncated string payload");
        f.seekg(8);
        len.resize(n); text.resize(size_t(n) * stride);
        f.read(reinterpret_cast<char*>(len.data()), size_t(n) * 4);
        f.read(text.data(), text.size());
        require(bool(f), "string payload read failed");
        for (int v : len) require(v >= 0 && v < stride, "string length exceeds DP array");
    }
};
int distance(const char* a, int n, const char* b, int m) {
    std::array<int, 109> row;
    for (int j = 0; j <= m; ++j) row[j] = j;
    for (int i = 1; i <= n; ++i) {
        int prev = row[0]; row[0] = i;
        for (int j = 1; j <= m; ++j) {
            int old = row[j];
            row[j] = std::min({row[j] + 1, row[j - 1] + 1, prev + (a[i - 1] != b[j - 1])});
            prev = old;
        }
    }
    return row[m];
}
int main(int argc, char** argv) {
    require(argc == 5, "usage: edit_oracle base.strb query.strb N output");
    Strings x(argv[1]), q(argv[2]);
    int n = std::stoi(argv[3]);
    require(n >= 10 && n <= x.n && n <= 10000000, "unavailable or disallowed N");
    require(access(argv[4], F_OK) != 0, "preserve existing oracle");
    std::string temporary = std::string(argv[4]) + ".partial." + std::to_string(getpid());
#ifdef _OPENMP
    omp_set_num_threads(std::min(32, omp_get_max_threads()));
#endif
    std::cerr << "exhaustive CPU edit oracle N=" << n << " queries=" << q.n << "\n" << std::flush;
    std::vector<int> ids(size_t(q.n) * 10);
    std::vector<double> ds(size_t(q.n) * 10);
#pragma omp parallel for schedule(dynamic, 1)
    for (int a = 0; a < q.n; ++a) {
        std::priority_queue<std::pair<int, int>> top;
        for (int i = 0; i < n; ++i) {
            int v = distance(x.text.data() + size_t(i) * x.stride, x.len[i],
                             q.text.data() + size_t(a) * q.stride, q.len[a]);
            if (top.size() < 10) top.emplace(v, i);
            else if (v < top.top().first) { top.pop(); top.emplace(v, i); }
        }
        for (int j = 9; j >= 0; --j) {
            ds[size_t(a) * 10 + j] = top.top().first;
            ids[size_t(a) * 10 + j] = top.top().second;
            top.pop();
        }
    }
    {
        std::ofstream out(temporary, std::ios::binary);
        out.write(reinterpret_cast<char*>(ids.data()), ids.size() * 4);
        out.write(reinterpret_cast<char*>(ds.data()), ds.size() * 8);
        out.close();
        require(bool(out), "oracle output failed");
    }
    require(link(temporary.c_str(), argv[4]) == 0, "refuse oracle replacement");
    require(unlink(temporary.c_str()) == 0, "oracle temporary unlink failed");
    std::cerr << "oracle complete bytes=" << ids.size() * 12 << "\n" << std::flush;
}
