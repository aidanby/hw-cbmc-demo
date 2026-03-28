// Direct-mapped write-back cache controller (4 lines, 8-bit address, 8-bit data).
//
// Address decomposition: addr[7:4]=tag, addr[3:2]=index (4 lines), addr[1:0]=ignored.
// Each line: valid bit, dirty bit, 4-bit tag, 8-bit data.
//
// Operations (active when req=1):
//   wr=0: READ  — if hit, return cached data; if miss, load from mem_rdata.
//   wr=1: WRITE — if hit, update cached data+dirty; if miss, allocate line.
//
// Writeback: when a dirty line is evicted on a miss, mem_wr pulses with
//   the old tag+data so the backing store can be updated.
//
// Three bugs corrupt the tag comparison, the dirty-bit writeback path,
// and the line-fill data source.
module cache_ctrl(
  input        clk,
  input        reset,
  input        req,          // memory request
  input        wr,           // 0=read, 1=write
  input  [7:0] addr,         // address
  input  [7:0] wdata,        // write data (for writes)
  input  [7:0] mem_rdata,    // data returning from backing store (for misses)
  output reg [7:0] rdata,    // read data output
  output reg       hit,      // cache hit
  output reg       mem_wr,   // writeback: pulse when dirty line evicted
  output reg [7:0] mem_waddr,// writeback: address of evicted line
  output reg [7:0] mem_wdata // writeback: data of evicted line
);
  // Cache storage
  reg       valid [0:3];
  reg       dirty [0:3];
  reg [3:0] tag   [0:3];
  reg [7:0] data  [0:3];

  // Address decomposition
  wire [3:0] req_tag   = addr[7:4];
  wire [1:0] req_index = addr[3:2];

  // Hit detection — compares tag AND valid
  wire cache_hit = valid[req_index] && (tag[req_index] == req_tag);

  initial begin
    rdata = 0; hit = 0; mem_wr = 0; mem_waddr = 0; mem_wdata = 0;
    valid[0] = 0; valid[1] = 0; valid[2] = 0; valid[3] = 0;
    dirty[0] = 0; dirty[1] = 0; dirty[2] = 0; dirty[3] = 0;
    tag[0] = 0; tag[1] = 0; tag[2] = 0; tag[3] = 0;
    data[0] = 0; data[1] = 0; data[2] = 0; data[3] = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      rdata <= 0; hit <= 0; mem_wr <= 0; mem_waddr <= 0; mem_wdata <= 0;
      valid[0] <= 0; valid[1] <= 0; valid[2] <= 0; valid[3] <= 0;
      dirty[0] <= 0; dirty[1] <= 0; dirty[2] <= 0; dirty[3] <= 0;
      tag[0] <= 0; tag[1] <= 0; tag[2] <= 0; tag[3] <= 0;
      data[0] <= 0; data[1] <= 0; data[2] <= 0; data[3] <= 0;
    end else begin
      hit    <= 1'b0;
      mem_wr <= 1'b0;

      if (req) begin
        if (cache_hit) begin
          // HIT path
          hit <= 1'b1;
          if (wr) begin
            data[req_index]  <= wdata;
            dirty[req_index] <= 1'b1;
          end else begin
            rdata <= data[req_index];
          end
        end else begin
          // MISS path — may need writeback first
          if (valid[req_index] && dirty[req_index]) begin
            // Evict dirty line: writeback
            mem_wr    <= 1'b1;
            mem_waddr <= {tag[req_index], req_index, 2'b00};
            mem_wdata <= data[req_tag]; // HINT: check this line carefully
          end
          // Fill new line
          valid[req_index] <= 1'b1;
          dirty[req_index] <= wr;
          tag[req_index]   <= req_tag;
          if (wr) begin
            data[req_index] <= wdata;
          end else begin
            data[req_index] <= wdata; // HINT: check this line carefully
          end
          rdata <= 8'd0;
        end
      end
    end
  end

  // Properties
  p_reset:     assert property (@(posedge clk) reset |=> !hit && !mem_wr);
  p_hit_valid: assert property (@(posedge clk) hit |-> valid[$past(req_index)] && tag[$past(req_index)] == $past(req_tag));
  p_read_hit:  assert property (@(posedge clk) !reset && req && !wr && cache_hit |=> hit && rdata == data[$past(req_index)]);
  p_write_hit: assert property (@(posedge clk) !reset && req && wr && cache_hit |=> dirty[$past(req_index)] == 1'b1);
  p_miss_fill: assert property (@(posedge clk) !reset && req && !wr && !cache_hit |=> valid[$past(req_index)] && tag[$past(req_index)] == $past(req_tag));
  p_wb_data:   assert property (@(posedge clk) mem_wr |-> mem_wdata == data[$past(req_index)]);
  p_miss_rdata: assert property (@(posedge clk) !reset && req && !wr && !cache_hit |=> rdata == $past(mem_rdata));
endmodule
