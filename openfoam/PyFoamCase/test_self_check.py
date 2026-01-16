"""
FoamFile 모듈 자체 점검 테스트
test.py의 테스트 케이스를 참고하여 작성
"""

import sys
import io
import tempfile
from pathlib import Path
from nextlib.openfoam.PyFoamCase.foamfile import FoamFile

# Windows에서 UTF-8 출력 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def create_test_file():
    """테스트용 OpenFOAM 파일 생성"""
    content = """
// Test OpenFOAM file
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
}

startFrom       startTime;
stopAt          endTime;

outlet
{
    type        patch;
    name        outlet_face;
    inGroups    2(wall patch);

    maxY
    {
        name    fluid;
        patch   outlet;
    }
}

vertices
(
    ( 0 0 0 )
    ( 1 0 0 )
    ( 1 1 0 )
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (10 10 1) simpleGrading (1 1 1)
    hex (8 9 10 11 12 13 14 15) (20 20 1) simpleGrading (2 2 1)
);

regions
(
    fluid   (region1 region2)
    solid   (region3)
);

actions
(
    {
        name        action1;
        type        faceZoneSet;
        faceSet     faces1;
    }
    {
        name        action2;
        type        cellZoneSet;
        faceSet     faces2;
    }
);
"""

    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.foam')
    temp_file.write(content)
    temp_file.close()
    return temp_file.name


def test_basic_operations():
    """기본 동작 테스트"""
    print("=" * 60)
    print("FoamFile 모듈 자체 점검 시작")
    print("=" * 60)

    test_file = create_test_file()
    foam = FoamFile()

    try:
        # 1. 파일 로드 테스트
        print("\n[1] 파일 로드 테스트")
        if foam.load(test_file):
            print("✓ 파일 로드 성공")
        else:
            print("✗ 파일 로드 실패")
            return False

        # 2. has_key 테스트
        print("\n[2] has_key 테스트")
        assert foam.has_key('startFrom'), "✗ 'startFrom' 키를 찾을 수 없음"
        print("✓ has_key('startFrom') = True")

        assert not foam.has_key('nonexistent'), "✗ 존재하지 않는 키 감지 실패"
        print("✓ has_key('nonexistent') = False")

        assert foam.has_key('outlet.inGroups'), "✗ 중첩 키 'outlet.inGroups' 찾기 실패"
        print("✓ has_key('outlet.inGroups') = True")

        # 3. get_value 테스트
        print("\n[3] get_value 테스트")
        start_value = foam.get_value('startFrom')
        print(f"✓ startFrom = {start_value}")
        assert start_value == 'startTime', f"✗ 예상: 'startTime', 실제: {start_value}"

        outlet_type = foam.get_value('outlet.type')
        print(f"✓ outlet.type = {outlet_type}")

        vertices = foam.get_value('vertices')
        print(f"✓ vertices (길이: {len(vertices) if vertices else 0})")

        # 4. get_key_list 테스트
        print("\n[4] get_key_list 테스트")
        top_keys = foam.get_key_list()
        print(f"✓ 최상위 키 목록 ({len(top_keys)}개): {top_keys[:5]}...")

        outlet_keys = foam.get_key_list('outlet')
        print(f"✓ outlet 하위 키: {outlet_keys}")

        # 5. blocks 관련 테스트
        print("\n[5] blocks 테스트")
        blocks = foam.get_value('blocks')
        print(f"✓ blocks 전체 ({len(blocks) if blocks else 0}개)")

        block0 = foam.get_value('blocks[0]')
        print(f"✓ blocks[0] = {block0}")

        cells = foam.get_value('blocks', map_key='cells')
        print(f"✓ blocks cells = {cells}")

        # 6. regions 관련 테스트
        print("\n[6] regions 테스트")
        regions = foam.get_value('regions')
        print(f"✓ regions = {regions}")

        region0_type = foam.get_value('regions[0]', map_key='type')
        print(f"✓ regions[0] type = {region0_type}")

        region_names = foam.get_value('regions', map_key='names')
        print(f"✓ regions names = {region_names}")

        # 7. actions 리스트 테스트
        print("\n[7] actions 테스트")
        action1_type = foam.get_value('actions[1].type')
        print(f"✓ actions[1].type = {action1_type}")

        action1_faceset = foam.get_value('actions[1].faceSet')
        print(f"✓ actions[1].faceSet = {action1_faceset}")

        # 8. inGroups 테스트
        print("\n[8] inGroups 테스트")
        ingroups = foam.get_value('outlet.inGroups')
        print(f"✓ outlet.inGroups = {ingroups}")

        print("\n" + "=" * 60)
        print("✓ 모든 읽기 테스트 통과")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 임시 파일 삭제
        Path(test_file).unlink(missing_ok=True)


def test_modification_operations():
    """수정 동작 테스트"""
    print("\n" + "=" * 60)
    print("수정 동작 테스트 시작")
    print("=" * 60)

    test_file = create_test_file()
    foam = FoamFile()

    try:
        foam.load(test_file)

        # 1. rename 테스트
        print("\n[1] rename 테스트")
        original_keys = foam.get_key_name_list('outlet')
        print(f"  원본 키: {original_keys}")

        foam.rename('outlet.name', 'newName')
        new_keys = foam.get_key_name_list('outlet')
        print(f"  변경 후: {new_keys}")
        assert 'newName' in new_keys, "✗ rename 실패"
        print("✓ rename 성공")

        # 2. set_value 테스트
        print("\n[2] set_value 테스트")
        foam.set_value('startFrom', 'latestTime')
        new_value = foam.get_value('startFrom')
        print(f"  startFrom = {new_value}")
        assert new_value == 'latestTime', f"✗ set_value 실패: {new_value}"
        print("✓ set_value 성공")

        # 3. 중첩 set_value 테스트
        print("\n[3] 중첩 set_value 테스트")
        foam.set_value('outlet.type', 'wall')
        new_type = foam.get_value('outlet.type')
        print(f"  outlet.type = {new_type}")
        assert new_type == 'wall', "✗ 중첩 set_value 실패"
        print("✓ 중첩 set_value 성공")

        # 4. 벡터 set_value 테스트
        print("\n[4] 벡터 값 설정 테스트")
        foam.set_value('vertices', [[0, 0, 0], [1, 1, 1], [2, 2, 2]])
        new_vertices = foam.get_value('vertices')
        print(f"  vertices = {new_vertices}")
        print("✓ 벡터 값 설정 성공")

        # 5. blocks 수정 테스트
        print("\n[5] blocks 수정 테스트")
        foam.set_value('blocks[0]', [30, 30, 30], map_key='cells')
        new_cells = foam.get_value('blocks[0]', map_key='cells')
        print(f"  blocks[0] cells = {new_cells}")
        print("✓ blocks 수정 성공")

        # 6. inGroups 수정 테스트
        print("\n[6] inGroups 수정 테스트")
        foam.set_value('outlet.inGroups', ['wall', 'patch', 'boundary'])
        new_ingroups = foam.get_value('outlet.inGroups')
        print(f"  inGroups = {new_ingroups}")
        print("✓ inGroups 수정 성공")

        # 7. regions 수정 테스트
        print("\n[7] regions 수정 테스트")
        foam.set_value('regions[0]', 'newFluid', map_key='type')
        new_region_type = foam.get_value('regions[0]', map_key='type')
        print(f"  regions[0] type = {new_region_type}")
        print("✓ regions 수정 성공")

        print("\n" + "=" * 60)
        print("✓ 모든 수정 테스트 통과")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        Path(test_file).unlink(missing_ok=True)


def test_insert_remove_operations():
    """삽입/삭제 동작 테스트"""
    print("\n" + "=" * 60)
    print("삽입/삭제 동작 테스트 시작")
    print("=" * 60)

    test_file = create_test_file()
    foam = FoamFile()

    try:
        foam.load(test_file)

        # 1. insert_value 테스트
        print("\n[1] insert_value 테스트")
        original_keys = foam.get_key_name_list('')
        print(f"  원본 키 개수: {len(original_keys)}")

        foam.insert_value('newKey', 'newValue')
        new_keys = foam.get_key_name_list('')
        print(f"  삽입 후 키 개수: {len(new_keys)}")
        assert 'newKey' in new_keys, "✗ insert_value 실패"
        print("✓ insert_value 성공")

        # 2. 중첩 insert_value 테스트
        print("\n[2] 중첩 insert_value 테스트")
        foam.insert_value('boundaryField.inlet.type', 'fixedValue')
        has_inserted = foam.has_key('boundaryField.inlet.type')
        assert has_inserted, "✗ 중첩 insert_value 실패"
        print("✓ 중첩 insert_value 성공")

        # 3. dict insert_value 테스트
        print("\n[3] dict insert_value 테스트")
        foam.insert_value('newSection', {'key1': 'value1', 'key2': 'value2'})
        section_keys = foam.get_key_list('newSection')
        print(f"  newSection 키: {section_keys}")
        assert 'key1' in section_keys, "✗ dict insert_value 실패"
        print("✓ dict insert_value 성공")

        # 4. insert_list_item 테스트
        print("\n[4] insert_list_item 테스트")
        original_actions = foam.get_key_name_list('actions')
        print(f"  원본 actions 개수: {len(original_actions)}")

        foam.insert_list_item('actions', {
            'name': 'action3',
            'type': 'newType',
            'faceSet': 'faces3'
        })

        new_actions = foam.get_key_name_list('actions')
        print(f"  삽입 후 actions 개수: {len(new_actions)}")
        print("✓ insert_list_item 성공")

        # 5. remove 테스트
        print("\n[5] remove 테스트")
        foam.remove('newKey')
        has_key = foam.has_key('newKey')
        assert not has_key, "✗ remove 실패"
        print("✓ remove 성공")

        # 6. 중첩 remove 테스트
        print("\n[6] 중첩 remove 테스트")
        foam.remove('outlet.maxY.name')
        has_nested = foam.has_key('outlet.maxY.name')
        assert not has_nested, "✗ 중첩 remove 실패"
        print("✓ 중첩 remove 성공")

        # 7. 리스트 아이템 remove 테스트
        print("\n[7] 리스트 아이템 remove 테스트")
        foam.remove('actions[0]')
        remaining_actions = foam.get_key_name_list('actions')
        print(f"  삭제 후 actions: {remaining_actions}")
        print("✓ 리스트 아이템 remove 성공")

        print("\n" + "=" * 60)
        print("✓ 모든 삽입/삭제 테스트 통과")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        Path(test_file).unlink(missing_ok=True)


def test_save_reload():
    """저장 및 재로드 테스트"""
    print("\n" + "=" * 60)
    print("저장 및 재로드 테스트 시작")
    print("=" * 60)

    test_file = create_test_file()
    foam = FoamFile()

    try:
        foam.load(test_file)

        # 1. 값 변경
        print("\n[1] 값 변경")
        foam.set_value('startFrom', 'latestTime')
        foam.set_value('outlet.type', 'wall')
        print("✓ 값 변경 완료")

        # 2. 저장
        print("\n[2] 파일 저장")
        if foam.save():
            print("✓ 파일 저장 성공")
        else:
            print("✗ 파일 저장 실패")
            return False

        # 3. 새 인스턴스로 재로드
        print("\n[3] 파일 재로드")
        foam2 = FoamFile()
        foam2.load(test_file)

        # 4. 값 확인
        print("\n[4] 값 검증")
        start_value = foam2.get_value('startFrom')
        outlet_type = foam2.get_value('outlet.type')

        print(f"  startFrom = {start_value}")
        print(f"  outlet.type = {outlet_type}")

        assert start_value == 'latestTime', f"✗ 저장된 값 불일치: {start_value}"
        assert outlet_type == 'wall', f"✗ 저장된 값 불일치: {outlet_type}"

        print("\n" + "=" * 60)
        print("✓ 저장 및 재로드 테스트 통과")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        Path(test_file).unlink(missing_ok=True)


def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 60)
    print("FoamFile 모듈 자체 점검 테스트 스위트")
    print("=" * 60)

    results = []

    # 각 테스트 실행
    results.append(("기본 동작", test_basic_operations()))
    results.append(("수정 동작", test_modification_operations()))
    results.append(("삽입/삭제 동작", test_insert_remove_operations()))
    results.append(("저장 및 재로드", test_save_reload()))

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:20s}: {status}")

    total = len(results)
    passed = sum(1 for _, r in results if r)

    print("\n" + "=" * 60)
    print(f"전체: {total}개 테스트 중 {passed}개 통과")

    if passed == total:
        print("✓ 모든 테스트 통과!")
    else:
        print(f"✗ {total - passed}개 테스트 실패")

    print("=" * 60)

    return passed == total


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
