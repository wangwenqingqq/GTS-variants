// Independent sequential row-label replay;all reads occur outside primary ACKs.
struct AckOracle {
    std::vector<int> labels;size_t at=0;uint64_t checked_rows=0,acks=0;
    explicit AckOracle(int n):labels(n){std::iota(labels.begin(),labels.end(),0);}
    void persist(const std::string& out)const{std::ofstream f(out+".ack_oracle.json");f<<"{\"passed\":true,\"ACK_callbacks\":"<<acks<<",\"changed_rows_checked\":"<<checked_rows<<",\"mutations_replayed\":"<<at<<"}\n";require(bool(f),"ACK proof export");}
    void after(Store& s,const std::vector<float>& x,const std::vector<float>& incoming){
        ++acks;std::set<int> touched;
        for(;at<s.mutations.size();at++){auto m=s.mutations[at];
            require(m.row>=0&&m.row<s.capacity,"oracle row range");
            if(m.kind==0){if(m.row!=m.last){labels[m.row]=labels[m.last];touched.insert(m.row);}}
            else{require(m.kind==1,"oracle mutation kind");labels[m.row]=m.id;touched.insert(m.row);}
        }
        std::array<float,960> row;
        for(int index:touched){int id=labels[index];const float* expected=id<s.capacity?x.data()+size_t(id)*960:incoming.data()+size_t(id-s.capacity)*960;
            ck(cudaMemcpyAsync(row.data(),s.p.database+size_t(index)*960,3840,cudaMemcpyDeviceToHost,s.p.stream));ck(cudaStreamSynchronize(s.p.stream));
            require(std::memcmp(row.data(),expected,3840)==0,"every changed allocated row after ACK");++checked_rows;
        }
    }
};
static void strict_capacity(Store& s,const std::vector<float>& x,const std::vector<float>& incoming,const std::string& out){
    std::vector<int> labels(s.capacity);std::iota(labels.begin(),labels.end(),0);
    for(auto m:s.mutations){if(m.kind==0){if(m.row!=m.last)labels[m.row]=labels[m.last];}else labels[m.row]=m.id;}
    std::vector<float> buffer(4096*960);uint64_t bytes=0;
    for(int start=0;start<s.capacity;start+=4096){int count=std::min(4096,s.capacity-start);
        ck(cudaMemcpyAsync(buffer.data(),s.p.database+size_t(start)*960,size_t(count)*3840,cudaMemcpyDeviceToHost,s.p.stream));ck(cudaStreamSynchronize(s.p.stream));
        for(int r=0;r<count;r++){int id=labels[start+r];const float* expected=id<s.capacity?x.data()+size_t(id)*960:incoming.data()+size_t(id-s.capacity)*960;
            require(std::memcmp(buffer.data()+size_t(r)*960,expected,3840)==0,"entire allocated database capacity,including retired rows");bytes+=3840;}
    }
    std::ofstream f(out+".capacity.json");f<<"{\"passed\":true,\"all_allocated_vector_bytes_compared\":"<<bytes<<",\"includes_retired_rows\":true}\n";require(bool(f),"capacity proof export");
}
