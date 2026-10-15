// Independent replay of original occurrence IDs and native mutation witnesses.
#include <vector>
#include <numeric>
#include <cstdint>
extern "C" int replay(int n,const int* victims,int k,int batch,int op,const int* records,int rows,
                      const int* physical,int live,const int* reverse,uint64_t* swaps){
    if(n<1||k<1||k>n/2||batch<1||batch>512||op<0||op>2)return 1;
    if(rows!=(op==1?k:2*k)||live!=(op==1?n-k:n))return 2;
    std::vector<int> f(n),r(n+k,-1);std::iota(f.begin(),f.end(),0);for(int i=0;i<n;i++)r[i]=i;
    int next=n,at=0;*swaps=0;
    auto same=[&](const int* e){for(int j=0;j<8;j++)if(records[size_t(at)*8+j]!=e[j])return false;++at;return true;};
    auto erase=[&](int begin,int count){for(int a=begin;a<begin+count;a++){
        int id=victims[a];if(id<0||id>=n||r[id]<0)return false;
        int size=int(f.size()),row=r[id],last=size-1,moved=row==last?-1:f.back();
        int e[8]={0,id,size,row,last,moved,next,size-1};if(!same(e))return false;
        if(row!=last){f[row]=moved;r[moved]=row;++*swaps;}f.pop_back();r[id]=-1;
    }return true;};
    auto insert=[&](int count){for(int a=0;a<count;a++){
        int size=int(f.size());if(next>=n+k||r[next]!=-1)return false;
        int e[8]={1,next,size,size,-1,-1,next+1,size+1};if(!same(e))return false;
        f.push_back(next);r[next]=size;++next;
    }return true;};
    if(op==0&&!erase(0,k))return 3;
    for(int a=0;a<k;a+=batch){int count=std::min(batch,k-a);
        if(op!=0&&!erase(a,count))return 4;
        if(op!=1&&!insert(count))return 5;
    }
    if(at!=rows||int(f.size())!=live)return 6;
    for(int i=0;i<live;i++)if(physical[i]!=f[i]||r[f[i]]!=i)return 7;
    for(int i=0;i<n+k;i++)if(reverse[i]!=r[i])return 8;
    return 0;
}
