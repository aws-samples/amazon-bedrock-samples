#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

from typing import TypeVar, TypedDict, Generic, Literal, NotRequired

T = TypeVar("T")


class CustomResourceRequest(TypedDict, Generic[T]):
    RequestType: Literal["Create", "Update", "Delete"]
    ResponseURL: str
    StackId: str
    RequestId: str
    ResourceType: str
    LogicalResourceId: str
    PhysicalResourceId: NotRequired[str]
    ResourceProperties: NotRequired[T]
    # OldResourceProperties: NotRequired[T]


class CustomResourceResponse(TypedDict):
    PhysicalResourceId: NotRequired[str]
    NoEcho: NotRequired[bool]
    Data: NotRequired[dict[str, str]]
