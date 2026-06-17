from __future__ import annotations

from urllib.parse import quote

from ..commute_plan import derive_commute_areas
from ..schema import RentProfile, SearchPlan, SearchRequest
from .registry import get_source_meta


CITY_DOMAINS = {
    "上海": {"beike_lianjia": "sh.zu.ke.com", "fang": "sh.zu.fang.com", "wellcee_city": "shanghai"},
    "北京": {"beike_lianjia": "bj.zu.ke.com", "fang": "zu.fang.com", "wellcee_city": "beijing"},
    "广州": {"beike_lianjia": "gz.zu.ke.com", "fang": "gz.zu.fang.com", "wellcee_city": "guangzhou"},
    "深圳": {"beike_lianjia": "sz.zu.ke.com", "fang": "sz.zu.fang.com", "wellcee_city": "shenzhen"},
}

AREA_SLUGS = {
    ("上海", "五角场"): {"beike_lianjia": "wujiaochang", "fang": "house-a026-b01647"},
    ("上海", "江湾体育场"): {"beike_lianjia": "jiangwantiyuchang", "fang": "house-a026-b01648"},
    ("上海", "控江路"): {"fang": "house-a026-b010350"},
    ("北京", "经海路"): {"beike_lianjia": "jinghailu"},
    ("北京", "次渠"): {"beike_lianjia": "ciqu"},
    ("北京", "次渠南"): {"beike_lianjia": "ciqunan"},
    ("北京", "马驹桥"): {"beike_lianjia": "majuqiao"},
}


def request_from_profile(profile: RentProfile, *, limit: int = 10, days: int = 7, sources: list[str] | None = None) -> SearchRequest:
    office = profile.office_anchor.get("office_name") or profile.office_anchor.get("address_hint")
    return SearchRequest(
        city=profile.office_anchor.get("city"),
        office_anchor=office,
        budget_min=profile.housing_constraints.get("budget_min"),
        budget_max=profile.housing_constraints.get("budget_max"),
        min_bedrooms=profile.housing_constraints.get("min_bedrooms"),
        days=days,
        limit=limit,
        sources=sources or profile.source_preferences.get("p0_order", ["beike_lianjia", "fang"]),
    )


def build_search_plan(request: SearchRequest, profile: RentProfile | None = None) -> SearchPlan:
    areas = []
    if profile:
        areas = profile.commute.get("derived_areas") or []
    areas = areas or derive_commute_areas(request.office_anchor)
    selected_sources = request.sources or ["beike_lianjia", "fang"]
    queries: dict[str, list[dict]] = {}
    for source_id in selected_sources:
        meta = get_source_meta(source_id)
        if not meta:
            continue
        built = _queries_for_source(source_id, request, areas)
        if built:
            queries[source_id] = built
    return SearchPlan(
        request=request,
        commute_areas=areas,
        source_queries=queries,
        open_questions=list(profile.open_questions if profile else []),
    )


def _queries_for_source(source_id: str, request: SearchRequest, areas: list[str]) -> list[dict]:
    city = request.city or "上海"
    domains = CITY_DOMAINS.get(city, CITY_DOMAINS["上海"])
    primary_area = next((area for area in areas if area), request.office_anchor or "")
    if source_id == "beike_lianjia":
        domain = domains["beike_lianjia"]
        slug = _area_slug(city, primary_area, source_id)
        path = f"/zufang/{slug}/" if slug else "/zufang/"
        return [{"url": f"https://{domain}{path}", "city": city, "area": primary_area, "days": request.days, "limit": request.limit}]
    if source_id == "lianjia_mobile_list":
        return _lianjia_mobile_list_queries(city, primary_area, request)
    if source_id == "fang":
        domain = domains["fang"]
        slug = _area_slug(city, primary_area, source_id)
        path = f"/{slug}/" if slug else "/"
        return [{
            "url": f"https://{domain}{path}",
            "city": city,
            "area": primary_area,
            "keyword": _keyword(request, primary_area),
            "days": request.days,
            "limit": request.limit,
        }]
    if source_id == "wellcee":
        city_slug = domains["wellcee_city"]
        keyword = quote(primary_area or city)
        return [{
            "url": f"https://www.wellcee.com/rent-apartment/{city_slug}?keyword={keyword}",
            "city": city,
            "area": primary_area,
            "days": request.days,
            "limit": request.limit,
            "warning": "Wellcee 当前没有稳定公开搜索解析入口，主要支持用户显式 URL/HTML 导入。",
        }]
    if source_id == "58":
        keyword = quote(_keyword(request, primary_area))
        return [{
            "url": f"https://m.58.com/{_city_slug_58(city)}/zufang/?key={keyword}",
            "city": city,
            "area": primary_area,
            "keyword": _keyword(request, primary_area),
            "days": request.days,
            "limit": request.limit,
            "discovery_only": True,
            "warning": "58 仅作为 Agent runtime discovery descriptor；未打开详情页前只能是 L0。",
        }]
    if source_id == "anjuke":
        keyword = quote(_keyword(request, primary_area))
        return [{
            "url": f"https://{_city_slug_anjuke(city)}.zu.anjuke.com/fangyuan/?kw={keyword}",
            "city": city,
            "area": primary_area,
            "keyword": _keyword(request, primary_area),
            "days": request.days,
            "limit": request.limit,
            "discovery_only": True,
            "warning": "安居客仅作为 Agent runtime discovery descriptor；需打开公开详情页才能升级 L1。",
        }]
    if source_id in {"douban", "douban_public_group"}:
        keyword = quote(f"{primary_area or city} 京东总部 租房")
        return [{
            "url": f"https://www.douban.com/search?q={keyword}",
            "city": city,
            "area": primary_area,
            "keyword": f"{primary_area or city} 京东总部 租房",
            "days": request.days,
            "limit": request.limit,
            "discovery_only": True,
            "warning": "豆瓣公开页只用于发现公开帖子；不得自动读取私域群或登录后内容。",
        }]
    if source_id == "lefull":
        keyword = quote(primary_area or "经海路")
        return [{
            "url": f"https://wb-v3.lefull.cn/Search/ContentSearch?keywords={keyword}",
            "city": city,
            "area": primary_area,
            "keyword": f"{primary_area or city} 乐乎 公寓",
            "days": request.days,
            "limit": request.limit,
            "discovery_only": True,
            "warning": "乐乎作为品牌公寓公开列表 descriptor；需打开页面核验价格、面积、押付和联系入口。",
        }]
    if source_id == "inboyu":
        return [{
            "url": "https://m.inboyu.com/shenzhen/site/online-book?project_id=39e400f9-63c6-171d-1800-0594a8509b9f",
            "city": city,
            "area": primary_area,
            "keyword": "泊寓 亦庄店 经海三路",
            "days": request.days,
            "limit": request.limit,
            "discovery_only": True,
            "warning": "泊寓公开页只用于过渡房源线索；约看需要用户人工提交手机号验证码。",
        }]
    if source_id == "brand_apartment_public":
        return [
            {
                "url": f"https://www.baidu.com/s?wd={quote(f'{primary_area or city} 乐乎 泊寓 蜂客 城家 有巢 京东总部')}",
                "city": city,
                "area": primary_area,
                "keyword": f"{primary_area or city} 品牌公寓 京东总部",
                "days": request.days,
                "limit": request.limit,
                "discovery_only": True,
                "warning": "品牌公寓公开 discovery descriptor；不得推进登录、预约或验证码流程。",
            }
        ]
    if source_id == "ziroom":
        keyword = quote(primary_area or city)
        return [{
            "url": f"https://www.ziroom.com/z/z2/?qwd={keyword}",
            "city": city,
            "area": primary_area,
            "keyword": _keyword(request, primary_area),
            "days": request.days,
            "limit": request.limit,
            "discovery_only": True,
            "warning": "自如/品牌公寓作为过渡选项 discovery descriptor；需核验服务费和退租条款。",
        }]
    return []


def _lianjia_mobile_list_queries(city: str, area: str, request: SearchRequest) -> list[dict]:
    if city != "北京":
        return []
    routes = [
        ("亦庄", "https://m.lianjia.com/chuzu/bj/brand/200301001000/yizhuang1/hk1rp4/"),
        ("亦庄 3000-4000", "https://m.lianjia.com/chuzu/bj/brand/200301001000/yizhuang1/orec1rp3/"),
        ("经开区", "https://m.lianjia.com/chuzu/bj/brand/200301001000/beijingjingjijishukaifaqu/in1rp0/"),
    ]
    return [
        {
            "url": url,
            "city": city,
            "area": area or label,
            "keyword": f"{label} 经海路 京东总部 一居 租房",
            "days": request.days,
            "limit": request.limit,
            "warning": "链家移动列表只做公开列表卡片抽取；详情页如被登录/安全中心拦截则记录 blocked。",
        }
        for label, url in routes
    ]


def _area_slug(city: str, area: str, source_id: str) -> str | None:
    for (known_city, keyword), slugs in AREA_SLUGS.items():
        if known_city == city and keyword in area:
            return slugs.get(source_id)
    return None


def _keyword(request: SearchRequest, area: str) -> str:
    bedroom = f"{request.min_bedrooms}居" if request.min_bedrooms else "一居"
    budget = f"{request.budget_max}以内" if request.budget_max else ""
    anchor = request.office_anchor or ""
    return " ".join(part for part in [area, anchor, bedroom, budget, "租房"] if part)


def _city_slug_58(city: str) -> str:
    return {"北京": "bj", "上海": "sh", "广州": "gz", "深圳": "sz"}.get(city, "bj")


def _city_slug_anjuke(city: str) -> str:
    return {"北京": "bj", "上海": "sh", "广州": "gz", "深圳": "sz"}.get(city, "bj")
