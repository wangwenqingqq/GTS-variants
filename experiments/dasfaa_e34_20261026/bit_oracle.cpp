// Independent exhaustive CPU Tanimoto top10; no CUDA or query indexing.
#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <limits>
#include <queue>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif

long long timestamp_ms() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}
void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
std::uint32_t read_le32(std::istream& f) {
    unsigned char bytes[4];
    f.read(reinterpret_cast<char*>(bytes), 4);
    require(bool(f), "truncated packed-bit header");
    return std::uint32_t(bytes[0]) | (std::uint32_t(bytes[1]) << 8)
         | (std::uint32_t(bytes[2]) << 16) | (std::uint32_t(bytes[3]) << 24);
}
struct Fingerprints {
    int rows;
    std::vector<std::uint64_t> words;
    explicit Fingerprints(const char* path, int prefix = 0) {
        std::ifstream f(path, std::ios::binary);
        require(bool(f), "cannot open packed-bit input");
        std::uint32_t count = read_le32(f), bits = read_le32(f);
        require(count > 0 && count <= std::uint32_t(INT32_MAX) && bits == 2048,
                "invalid packed-bit dimensions");
        f.seekg(0, std::ios::end);
        require(f.tellg() == std::streamoff(8 + std::uint64_t(count) * 256),
                "invalid packed-bit payload size");
        rows = prefix ? prefix : int(count);
        require(rows > 0 && std::uint32_t(rows) <= count, "unavailable packed-bit prefix");
        words.resize(std::size_t(rows) * 32);
        f.seekg(8);
        f.read(reinterpret_cast<char*>(words.data()), std::streamsize(words.size() * 8));
        require(bool(f), "packed-bit payload read failed");
        const std::uint16_t endian = 1;
        if (*reinterpret_cast<const unsigned char*>(&endian) != 1)
            for (auto& word : words) word = __builtin_bswap64(word);
    }
    const std::uint64_t* row(int i) const { return words.data() + std::size_t(i) * 32; }
};
double distance(const std::uint64_t* a, const std::uint64_t* b) {
    int common = 0, combined = 0;
    for (int i = 0; i < 32; ++i) {
        common += __builtin_popcountll(a[i] & b[i]);
        combined += __builtin_popcountll(a[i] | b[i]);
    }
    return combined ? 1.0 - double(common) / double(combined) : 0.0;
}
void append_le(std::vector<unsigned char>& bytes, std::uint64_t value, int count) {
    for (int i = 0; i < count; ++i) bytes.push_back((value >> (i * 8)) & 255);
}
void publish(const char* path, const std::vector<unsigned char>& bytes) {
    std::string partial = std::string(path) + ".partial." + std::to_string(getpid());
    int fd = open(partial.c_str(), O_WRONLY | O_CREAT | O_EXCL, 0600);
    require(fd >= 0, "refuse existing or unwritable partial oracle");
    std::size_t offset = 0;
    while (offset < bytes.size()) {
        ssize_t count = write(fd, bytes.data() + offset, bytes.size() - offset);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) { close(fd); throw std::runtime_error("partial oracle write failed"); }
        offset += std::size_t(count);
    }
    int sync_error = fsync(fd), close_error = close(fd);
    require(sync_error == 0 && close_error == 0, "partial oracle flush failed");
    // A hard link publishes a complete inode atomically and cannot replace path.
    require(link(partial.c_str(), path) == 0, "refuse oracle replacement or invalid output path");
    require(unlink(partial.c_str()) == 0, "oracle published but partial unlink failed");
}
int main(int argc, char** argv) {
    try {
        require(argc == 5, "usage: bit_oracle base.bits query.bits N output.oracle");
        std::size_t parsed;
        long long requested = std::stoll(argv[3], &parsed);
        require(parsed == std::strlen(argv[3]) && requested >= 10 && requested <= INT32_MAX,
                "invalid oracle N");
        // lstat notices dangling symlinks as well as regular existing outputs.
        struct stat st;
        require(lstat(argv[4], &st) != 0 && errno == ENOENT, "preserve existing oracle");
        Fingerprints x(argv[1], int(requested)), query(argv[2]);
        int threads = 1;
#ifdef _OPENMP
        omp_set_dynamic(0);
        threads = std::min(32, omp_get_max_threads());
        omp_set_num_threads(threads);
#endif
        std::cerr << "time_unix_ms=" << timestamp_ms() << " exhaustive CPU bit oracle N=" << x.rows << " queries=" << query.rows
                  << " threads=" << threads << " empty_union_distance=0\n" << std::flush;
        auto begin = std::chrono::steady_clock::now();
        std::vector<std::int32_t> ids(std::size_t(query.rows) * 10);
        std::vector<double> distances(ids.size());
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 1)
#endif
        for (int qi = 0; qi < query.rows; ++qi) {
            std::priority_queue<std::pair<double, int>> top;
            for (int id = 0; id < x.rows; ++id) {
                std::pair<double, int> entry(distance(x.row(id), query.row(qi)), id);
                if (top.size() < 10) top.push(entry);
                else if (entry < top.top()) { top.pop(); top.push(entry); }
            }
            for (int j = 9; j >= 0; --j) {
                distances[std::size_t(qi) * 10 + j] = top.top().first;
                ids[std::size_t(qi) * 10 + j] = top.top().second;
                top.pop();
            }
        }
        std::vector<unsigned char> bytes;
        bytes.reserve(ids.size() * 12);
        for (auto id : ids) append_le(bytes, std::uint32_t(id), 4);
        for (double value : distances) {
            std::uint64_t encoded;
            static_assert(sizeof(value) == sizeof(encoded) && std::numeric_limits<double>::is_iec559,
                          "IEEE FP64 oracle format required");
            std::memcpy(&encoded, &value, sizeof(value));
            append_le(bytes, encoded, 8);
        }
        publish(argv[4], bytes);
        double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - begin).count();
        std::cerr << "time_unix_ms=" << timestamp_ms() << " oracle complete bytes=" << bytes.size() << " seconds=" << seconds << '\n' << std::flush;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "time_unix_ms=" << timestamp_ms() << " bit_oracle: " << error.what() << '\n' << std::flush;
        return 2;
    }
}
