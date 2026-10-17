// Independent sequential ownership replay;never uses either GPU planner.
#include <vector>
#include <numeric>
#include <cstdint>
extern "C" int replay(int n,const int* victims,int k,int batch,const int* ends,
                      const int* records,const int* physical,const int* reverse,uint64_t* swaps){
    if(n<1||k<1||k>n/2||batch<1||batch>512||ends[0]!=0||ends[4]!=k)return 1;
    std::vector<int> f(n),r(n+k,-1);std::iota(f.begin(),f.end(),0);for(int i=0;i<n;i++)r[i]=i;
    int next=n,at=0,cursor=0;*swaps=0;
    auto same=[&](const int* expect){if(at>=2*k)return false;for(int j=0;j<8;j++)if(records[size_t(at)*8+j]!=expect[j])return false;++at;return true;};
    for(int phase=0;phase<5;phase++)while(cursor<ends[phase]){
        int count=std::min(batch,ends[phase]-cursor);
        for(int a=cursor;a<cursor+count;a++){
            int id=victims[a];if(id<0||id>=next||r[id]<0)return 2;
            int size=int(f.size()),row=r[id],last=size-1,moved=row==last?-1:f.back();
            int expected[8]={0,id,size,row,last,moved,next,size-1};if(!same(expected))return 3;
            if(row!=last){f[row]=moved;r[moved]=row;++*swaps;}f.pop_back();r[id]=-1;
        }
        for(int a=0;a<count;a++){
            int size=int(f.size());if(next>=n+k||r[next]!=-1)return 4;
            int expected[8]={1,next,size,size,-1,-1,next+1,size+1};if(!same(expected))return 5;
            f.push_back(next);r[next]=size;++next;
        }
        cursor+=count;
    }
    if(at!=2*k||next!=n+k||int(f.size())!=n)return 6;
    for(int i=0;i<n;i++)if(physical[i]!=f[i]||r[f[i]]!=i)return 7;
    for(int i=0;i<n+k;i++)if(reverse[i]!=r[i])return 8;
    return 0;
}
