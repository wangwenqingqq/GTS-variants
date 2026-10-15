// Independent replay of actual transition witnesses; full final maps are compared.
#include <cstdint>
#include <vector>
#include <numeric>
extern "C" int check_mutations(int n,const int* victims,int total,int workload,
    const int* records,int rows,const int* actual_physical,const int* actual_reverse,uint64_t* swaps){
    if(n<1||total<1||rows!=2*total)return 1;
    std::vector<int> forward(n),reverse(n+total,-1);std::iota(forward.begin(),forward.end(),0);std::iota(reverse.begin(),reverse.begin()+n,0);
    int cursor=0,next=n,at=0;*swaps=0;
    int ends[5]={0,0,0,0,0};
    if(workload==0){for(int i=1;i<5;i++)ends[i]=i*4;}
    else if(workload==1){for(int i=1;i<5;i++)ends[i]=i*16;}
    else if(workload==2){ends[1]=n/20;ends[2]=n/5;ends[3]=n*35/100;ends[4]=n/2;}
    else return 2;
    if(total!=ends[4])return 3;
    auto same=[&](const int* expect){for(int j=0;j<8;j++)if(records[size_t(at)*8+j]!=expect[j])return false;++at;return true;};
    for(int phase=1;phase<5;phase++)while(cursor<ends[phase]){
        int count=workload==2?512:1;if(count>ends[phase]-cursor)count=ends[phase]-cursor;
        for(int r=0;r<count;r++){
            int id=victims[cursor+r];if(id<0||id>=n||reverse[id]<0)return 4;
            int size=int(forward.size()),row=reverse[id],last=size-1,moved=row==last?-1:forward.back();
            int expected[8]={0,id,size,row,last,moved,next,size-1};if(!same(expected))return 5;
            if(row!=last){forward[row]=moved;reverse[moved]=row;++*swaps;}forward.pop_back();reverse[id]=-1;
        }
        for(int r=0;r<count;r++){
            int size=int(forward.size());if(next>=n+total||reverse[next]!=-1)return 6;
            int expected[8]={1,next,size,size,-1,-1,next+1,size+1};if(!same(expected))return 7;
            forward.push_back(next);reverse[next]=size;++next;
        }
        cursor+=count;
    }
    if(at!=rows||int(forward.size())!=n)return 8;
    for(int i=0;i<n;i++)if(forward[i]!=actual_physical[i]||reverse[forward[i]]!=i)return 9;
    for(int i=0;i<n+total;i++)if(reverse[i]!=actual_reverse[i])return 10;
    return 0;
}
